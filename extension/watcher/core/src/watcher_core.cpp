#include "watcher_core.hpp"
#include <sys/ioctl.h>
#include <linux/userfaultfd.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <string.h>
#include <fstream>
#include <sstream>
#include <thread>
#include <mutex>
#include <queue>
#include <unordered_map>
#include <atomic>
#include <cstring>
#include <cstdio>
#include <errno.h>
#include <sys/syscall.h>
#include <linux/fs.h>

namespace watcher {

// ============================================================================
// Lock-Free Event Queue (SPSC - Single Producer, Single Consumer pattern)
// ============================================================================

class EventQueue {
private:
    struct Node {
        FastPathEvent event;
        Node* next;
    };
    
    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    size_t capacity_;
    std::atomic<size_t> size_;

public:
    EventQueue(size_t capacity) : capacity_(capacity), size_(0) {
        Node* sentinel = new Node();
        head_.store(sentinel, std::memory_order_relaxed);
        tail_.store(sentinel, std::memory_order_relaxed);
    }
    
    ~EventQueue() {
        Node* node = head_.load(std::memory_order_relaxed);
        while (node) {
            Node* next = node->next;
            delete node;
            node = next;
        }
    }
    
    bool enqueue(const FastPathEvent& event) {
        if (size_.load(std::memory_order_acquire) >= capacity_) {
            return false;  // Queue full
        }
        
        Node* new_node = new Node();
        new_node->event = event;
        new_node->next = nullptr;
        
        Node* old_tail = tail_.load(std::memory_order_relaxed);
        tail_.store(new_node, std::memory_order_release);
        old_tail->next = new_node;
        
        size_.fetch_add(1, std::memory_order_acq_rel);
        return true;
    }
    
    bool dequeue(FastPathEvent& event) {
        Node* old_head = head_.load(std::memory_order_relaxed);
        Node* next = old_head->next;
        
        if (!next) {
            return false;  // Queue empty
        }
        
        event = next->event;
        head_.store(next, std::memory_order_release);
        
        delete old_head;
        size_.fetch_sub(1, std::memory_order_acq_rel);
        return true;
    }
    
    size_t size() const {
        return size_.load(std::memory_order_acquire);
    }
};

// ============================================================================
// Symbol Cache (LRU with TTL)
// ============================================================================

class SymbolCache {
private:
    struct Entry {
        std::string symbol;
        std::string file;
        int line;
        std::chrono::system_clock::time_point timestamp;
    };
    
    std::unordered_map<uint64_t, Entry> cache_;
    std::mutex mutex_;
    static constexpr int64_t TTL_SECONDS = 3600;
    
public:
    bool get(uint64_t ip, std::string& symbol, std::string& file, int& line) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = cache_.find(ip);
        if (it == cache_.end()) {
            return false;
        }
        
        // Check TTL
        auto now = std::chrono::system_clock::now();
        auto age = std::chrono::duration_cast<std::chrono::seconds>(now - it->second.timestamp).count();
        if (age > TTL_SECONDS) {
            cache_.erase(it);
            return false;
        }
        
        symbol = it->second.symbol;
        file = it->second.file;
        line = it->second.line;
        return true;
    }
    
    void set(uint64_t ip, const std::string& symbol, const std::string& file, int line) {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_[ip] = {symbol, file, line, std::chrono::system_clock::now()};
    }
    
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.clear();
    }
};

// ============================================================================
// Watcher Core Implementation
// ============================================================================

class WatcherCoreImpl final : public WatcherCore {
private:
    State state_;
    std::mutex state_mutex_;
    std::string error_message_;
    std::string output_dir_;
    
    std::unique_ptr<EventQueue> event_queue_;
    std::unordered_map<std::string, VariableMetadata> variables_;
    std::mutex variables_mutex_;
    
    SymbolCache symbol_cache_;
    
    int uffd_;
    std::thread handler_thread_;
    std::thread slow_path_thread_;
    std::atomic<bool> running_;
    
    // Metrics
    std::atomic<uint64_t> events_received_;
    std::atomic<uint64_t> events_processed_;
    std::atomic<uint64_t> events_dropped_;
    
    static WatcherCoreImpl& getInstanceImpl() {
        static WatcherCoreImpl instance;
        return instance;
    }
    
    friend class WatcherCore;
    
public:
    WatcherCoreImpl() 
        : state_(UNINITIALIZED), uffd_(-1), running_(false),
          events_received_(0), events_processed_(0), events_dropped_(0) {}
    
    ~WatcherCoreImpl() {
        if (state_ != UNINITIALIZED && state_ != STOPPED && state_ != ERROR) {
            stop(1000);
        }
        if (uffd_ >= 0) {
            close(uffd_);
        }
    }
    
    bool initialize(const std::string& output_dir, size_t max_queue_size) override {
        std::lock_guard<std::mutex> lock(state_mutex_);
        
        if (state_ != UNINITIALIZED) {
            error_message_ = "Core already initialized";
            return false;
        }
        
        output_dir_ = output_dir;
        event_queue_ = std::make_unique<EventQueue>(max_queue_size);
        
        // Initialize userfaultfd
        uffd_ = syscall(__NR_userfaultfd, O_CLOEXEC | O_NONBLOCK);
        if (uffd_ < 0) {
            error_message_ = std::string("Failed to create userfaultfd: ") + strerror(errno);
            state_ = ERROR;
            return false;
        }
        
        // Enable thread ID feature
        struct uffdio_api api = {};
        api.api = UFFD_API;
        api.features = UFFD_FEATURE_THREAD_ID | UFFD_FEATURE_PAGEFAULT_FLAG_WP;
        
        if (ioctl(uffd_, UFFDIO_API, &api) < 0) {
            error_message_ = std::string("Failed to configure userfaultfd: ") + strerror(errno);
            state_ = ERROR;
            close(uffd_);
            uffd_ = -1;
            return false;
        }
        
        state_ = INITIALIZED;
        return true;
    }
    
    std::string registerPage(void* page_base, size_t page_size, const std::string& name,
                            EventFlags flags, const MutationDepth& mutation_depth) override {
        std::lock_guard<std::mutex> lock(variables_mutex_);
        
        if (state_ == STOPPED || state_ == ERROR) {
            return "";
        }
        
        // Generate UUID (simplified - using timestamp + counter in production use uuid lib)
        static std::atomic<uint64_t> counter(0);
        std::stringstream ss;
        ss << "var-" << std::chrono::system_clock::now().time_since_epoch().count() 
           << "-" << counter.fetch_add(1);
        std::string variable_id = ss.str();
        
        // Register with userfaultfd if running
        if (state_ == RUNNING || state_ == PAUSED) {
            struct uffdio_register reg = {};
            reg.range.start = reinterpret_cast<uint64_t>(page_base);
            reg.range.len = page_size;
            reg.mode = UFFDIO_REGISTER_MODE_WP;
            
            if (ioctl(uffd_, UFFDIO_REGISTER, &reg) < 0) {
                return "";  // Registration failed
            }
        }
        
        // Read initial snapshot
        std::vector<uint8_t> snapshot(page_size);
        if (!page_base) {
            error_message_ = "Cannot snapshot null page_base address";
            return "";
        }
        // Note: memcpy will fail at runtime if page_base is invalid
        // Caller guarantees page is touched and valid
        memcpy(snapshot.data(), page_base, page_size);
        
        // Store metadata
        VariableMetadata meta;
        meta.variable_id = variable_id;
        meta.page_base = page_base;
        meta.page_size = page_size;
        meta.name = name;
        meta.flags = flags;
        meta.mutation_depth = mutation_depth;
        meta.initial_snapshot = snapshot;
        meta.registered_at = std::chrono::system_clock::now();
        
        variables_[variable_id] = meta;
        return variable_id;
    }
    
    bool unregisterPage(const std::string& variable_id) override {
        std::lock_guard<std::mutex> lock(variables_mutex_);
        
        auto it = variables_.find(variable_id);
        if (it == variables_.end()) {
            return false;
        }
        
        if (state_ == RUNNING || state_ == PAUSED) {
            // Note: uffdio_unregister is not always available in all Linux versions
            // For now, we just track the variable removal in our registry
            // Kernel will clean up on close(uffd)
        }
        
        variables_.erase(it);
        return true;
    }
    
    std::vector<uint8_t> readSnapshot(const std::string& variable_id) override {
        std::lock_guard<std::mutex> lock(variables_mutex_);
        
        auto it = variables_.find(variable_id);
        if (it == variables_.end()) {
            return {};
        }
        
        return it->second.initial_snapshot;
    }
    
    bool writeSnapshot(const std::string& variable_id, const std::vector<uint8_t>& snapshot) override {
        std::lock_guard<std::mutex> lock(variables_mutex_);
        
        auto it = variables_.find(variable_id);
        if (it == variables_.end()) {
            return false;
        }
        
        it->second.initial_snapshot = snapshot;
        return true;
    }
    
    bool updateMetadata(const std::string& variable_id, const VariableMetadata& metadata) override {
        std::lock_guard<std::mutex> lock(variables_mutex_);
        
        auto it = variables_.find(variable_id);
        if (it == variables_.end()) {
            return false;
        }
        
        variables_[variable_id] = metadata;
        return true;
    }
    
    bool start() override {
        std::lock_guard<std::mutex> lock(state_mutex_);
        
        if (state_ != INITIALIZED) {
            error_message_ = "Core not initialized";
            return false;
        }
        
        running_ = true;
        state_ = RUNNING;
        
        handler_thread_ = std::thread(&WatcherCoreImpl::handlerLoop, this);
        slow_path_thread_ = std::thread(&WatcherCoreImpl::slowPathLoop, this);
        
        return true;
    }
    
    bool pause() override {
        std::lock_guard<std::mutex> lock(state_mutex_);
        
        if (state_ != RUNNING) {
            error_message_ = "Core not running";
            return false;
        }
        
        state_ = PAUSED;
        return true;
    }
    
    bool resume() override {
        std::lock_guard<std::mutex> lock(state_mutex_);
        
        if (state_ != PAUSED) {
            error_message_ = "Core not paused";
            return false;
        }
        
        state_ = RUNNING;
        return true;
    }
    
    bool stop(int timeout_ms) override {
        std::lock_guard<std::mutex> lock(state_mutex_);
        
        if (state_ == STOPPED || state_ == ERROR || state_ == UNINITIALIZED) {
            return state_ != ERROR;
        }
        
        running_ = false;
        state_ = STOPPED;
        
        // Wait for threads with timeout
        auto start = std::chrono::system_clock::now();
        while (handler_thread_.joinable() && 
               std::chrono::duration_cast<std::chrono::milliseconds>(
                   std::chrono::system_clock::now() - start).count() < timeout_ms) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        
        if (handler_thread_.joinable()) {
            handler_thread_.detach();
        }
        if (slow_path_thread_.joinable()) {
            slow_path_thread_.detach();
        }
        
        return true;
    }
    
    State getState() const override {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(state_mutex_));
        return state_;
    }
    
    std::string getErrorMessage() const override {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(state_mutex_));
        return error_message_;
    }
    
    EnrichedEvent* dequeueEvent() override {
        // Not implemented in this phase - placeholder
        return nullptr;
    }
    
    Metrics getMetrics() const override {
        return Metrics{
            events_received_.load(),
            events_processed_.load(),
            events_dropped_.load(),
            0,  // callbacks_failed
            0.0,  // mean_latency_ms
            static_cast<uint32_t>(event_queue_ ? event_queue_->size() : 0)
        };
    }

private:
    void handlerLoop() {
        struct pollfd pfd = {};
        pfd.fd = uffd_;
        pfd.events = POLLIN;
        
        std::vector<struct uffd_msg> msgs(16);
        
        while (running_) {
            int poll_ret = poll(&pfd, 1, 100);  // 100ms timeout
            
            if (poll_ret <= 0) {
                continue;
            }
            
            ssize_t nread = read(uffd_, msgs.data(), msgs.size() * sizeof(struct uffd_msg));
            if (nread <= 0) {
                continue;
            }
            
            size_t num_msgs = nread / sizeof(struct uffd_msg);
            for (size_t i = 0; i < num_msgs; ++i) {
                if (msgs[i].event & UFFD_EVENT_PAGEFAULT) {
                    handlePageFault(msgs[i]);
                }
            }
        }
    }
    
    void handlePageFault(const struct uffd_msg& msg) {
        uint64_t page_base = msg.arg.pagefault.address & ~(PAGE_SIZE - 1);
        uint64_t fault_addr = msg.arg.pagefault.address;
        pid_t tid = msg.arg.pagefault.feat.ptid;
        
        // Extract instruction pointer from /proc/<tid>/syscall
        uint64_t ip = extractInstructionPointer(tid);
        
        // Create fast-path event
        FastPathEvent event;
        event.event_id = "evt-" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        event.ts_ns = std::chrono::system_clock::now().time_since_epoch().count() * 1000000;
        event.page_base = reinterpret_cast<void*>(page_base);
        event.fault_addr = reinterpret_cast<void*>(fault_addr);
        event.tid = tid;
        event.ip = ip;
        
        // Enqueue event
        if (!event_queue_->enqueue(event)) {
            events_dropped_.fetch_add(1);
        } else {
            events_received_.fetch_add(1);
        }
        
        // Unprotect page (allow write to complete)
        struct uffdio_writeprotect wp = {};
        wp.range.start = page_base;
        wp.range.len = PAGE_SIZE;
        wp.mode = 0;  // Unprotect
        if (ioctl(uffd_, UFFDIO_WRITEPROTECT, &wp) < 0) {
            events_dropped_.fetch_add(1);
            return;
        }
        
        // Re-protect page
        wp.mode = UFFDIO_WRITEPROTECT_MODE_WP;
        if (ioctl(uffd_, UFFDIO_WRITEPROTECT, &wp) < 0) {
            events_dropped_.fetch_add(1);
        }
    }
    
    uint64_t extractInstructionPointer(pid_t tid) {
        // Read /proc/<tid>/syscall to get instruction pointer
        std::string path = "/proc/" + std::to_string(tid) + "/syscall";
        std::ifstream file(path);
        if (!file) {
            return 0;
        }
        
        std::string line;
        if (std::getline(file, line)) {
            // Last field is the instruction pointer in hex
            size_t last_space = line.rfind(' ');
            if (last_space != std::string::npos) {
                std::string hex_str = line.substr(last_space + 1);
                try {
                    return std::stoull(hex_str, nullptr, 16);
                } catch (...) {
                    return 0;
                }
            }
        }
        
        return 0;
    }
    
    void slowPathLoop() {
        while (running_) {
            // Process queued events in batches
            // This is a placeholder - actual implementation will:
            // 1. Dequeue event
            // 2. Read post-snapshot
            // 3. Compute deltas
            // 4. Resolve symbols
            // 5. Persist to JSONL
            // 6. Call custom processor
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
};

// ============================================================================
// Public API Implementation
// ============================================================================

WatcherCore& WatcherCore::getInstance() {
    static WatcherCoreImpl instance;
    return instance;
}

bool WatcherCore::initialize(const std::string& output_dir, size_t max_queue_size) {
    return static_cast<WatcherCoreImpl&>(*this).initialize(output_dir, max_queue_size);
}

std::string WatcherCore::registerPage(void* page_base, size_t page_size, const std::string& name,
                                     EventFlags flags, const MutationDepth& mutation_depth) {
    return static_cast<WatcherCoreImpl&>(*this).registerPage(page_base, page_size, name, flags, mutation_depth);
}

bool WatcherCore::unregisterPage(const std::string& variable_id) {
    return static_cast<WatcherCoreImpl&>(*this).unregisterPage(variable_id);
}

std::vector<uint8_t> WatcherCore::readSnapshot(const std::string& variable_id) {
    return static_cast<WatcherCoreImpl&>(*this).readSnapshot(variable_id);
}

bool WatcherCore::writeSnapshot(const std::string& variable_id, const std::vector<uint8_t>& snapshot) {
    return static_cast<WatcherCoreImpl&>(*this).writeSnapshot(variable_id, snapshot);
}

bool WatcherCore::updateMetadata(const std::string& variable_id, const VariableMetadata& metadata) {
    return static_cast<WatcherCoreImpl&>(*this).updateMetadata(variable_id, metadata);
}

bool WatcherCore::start() {
    return static_cast<WatcherCoreImpl&>(*this).start();
}

bool WatcherCore::pause() {
    return static_cast<WatcherCoreImpl&>(*this).pause();
}

bool WatcherCore::resume() {
    return static_cast<WatcherCoreImpl&>(*this).resume();
}

bool WatcherCore::stop(int timeout_ms) {
    return static_cast<WatcherCoreImpl&>(*this).stop(timeout_ms);
}

WatcherCore::State WatcherCore::getState() const {
    return static_cast<const WatcherCoreImpl&>(*this).getState();
}

std::string WatcherCore::getErrorMessage() const {
    return static_cast<const WatcherCoreImpl&>(*this).getErrorMessage();
}

EnrichedEvent* WatcherCore::dequeueEvent() {
    return static_cast<WatcherCoreImpl&>(*this).dequeueEvent();
}

WatcherCore::Metrics WatcherCore::getMetrics() const {
    return static_cast<const WatcherCoreImpl&>(*this).getMetrics();
}

}  // namespace watcher
