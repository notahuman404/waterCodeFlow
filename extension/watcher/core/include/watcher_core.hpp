#pragma once

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <memory>
#include <chrono>

namespace watcher {

// ============================================================================
// Constants & Configuration
// ============================================================================

constexpr size_t PAGE_SIZE = 4096;
constexpr size_t HEADER_SIZE = 64;
constexpr size_t MAX_CONCURRENT_WORKERS = 3;
constexpr size_t EVENT_QUEUE_CAPACITY = 10000;
constexpr uint32_t MAGIC = 0xFDB10001;

// ============================================================================
// Data Structures
// ============================================================================

// Event flags for registration
enum EventFlags : uint32_t {
    FLAG_TRACK_THREADS = 1 << 0,
    FLAG_TRACK_SQL = 1 << 1,
    FLAG_TRACK_ALL = 1 << 2,
    FLAG_TRACK_LOCALS = 1 << 3,
};

// Mutation depth specification
struct MutationDepth {
    bool full_page;
    size_t byte_range;  // Only if full_page == false
};

// Minimal fast-path event (enqueued immediately on fault)
struct FastPathEvent {
    std::string event_id;  // UUID
    uint64_t ts_ns;        // Timestamp in nanoseconds
    void* page_base;       // Page address (not offset)
    void* fault_addr;      // Exact fault address
    pid_t tid;             // Thread ID
    uint64_t ip;           // Instruction pointer
};

// Full event after enrichment (slow-path)
struct EnrichedEvent {
    std::string event_id;
    uint64_t ts_ns;
    void* page_base;
    void* fault_addr;
    pid_t tid;
    uint64_t ip;
    std::string symbol;           // Function name or "??"
    std::string file;             // Source file path
    int line;                      // Line number
    std::vector<uint8_t> pre_snapshot;   // Before state
    std::vector<uint8_t> post_snapshot;  // After state
    std::vector<std::pair<size_t, std::pair<std::vector<uint8_t>, std::vector<uint8_t>>>> deltas;  // (offset, (old, new))
    std::vector<std::string> variable_ids;
    std::string sql_context_id;   // Optional SQL context
};

// Variable registration metadata
struct VariableMetadata {
    std::string variable_id;      // UUID
    void* page_base;
    size_t page_size;
    std::string name;
    EventFlags flags;
    MutationDepth mutation_depth;
    std::vector<uint8_t> initial_snapshot;
    std::chrono::system_clock::time_point registered_at;
};

// ============================================================================
// Core API
// ============================================================================

class WatcherCore {
public:
    /// Get singleton instance
    static WatcherCore& getInstance();
    
    /// Initialize with configuration
    /// @param output_dir Directory for JSONL output
    /// @param max_queue_size Maximum event queue capacity
    /// @return true on success
    virtual bool initialize(const std::string& output_dir, size_t max_queue_size = EVENT_QUEUE_CAPACITY) = 0;
    
    /// Register a page for watching
    /// Caller guarantees: page is touched, page lifetime >= watch lifetime
    /// @param page_base Base address of the page (must be 4K aligned)
    /// @param page_size Size of page (typically 4096)
    /// @param name Human-readable variable name
    /// @param flags Event flags (TRACK_THREADS, TRACK_SQL, etc.)
    /// @param mutation_depth How deep to track mutations
    /// @return variable_id (UUID) on success, empty string on error
    virtual std::string registerPage(void* page_base, size_t page_size, const std::string& name,
                            EventFlags flags, const MutationDepth& mutation_depth) = 0;
    
    /// Unregister a watched page
    /// @param variable_id The ID returned from registerPage
    /// @return true on success
    virtual bool unregisterPage(const std::string& variable_id) = 0;
    
    /// Read current snapshot of a watched variable
    /// @param variable_id The variable to snapshot
    /// @return Snapshot bytes, or empty on error
    virtual std::vector<uint8_t> readSnapshot(const std::string& variable_id) = 0;
    
    /// Write/update snapshot (for pre-state capture)
    /// @param variable_id The variable to update
    /// @param snapshot New snapshot bytes
    /// @return true on success
    virtual bool writeSnapshot(const std::string& variable_id, const std::vector<uint8_t>& snapshot) = 0;
    
    /// Update metadata for a variable
    /// @param variable_id The variable to update
    /// @param metadata New metadata
    /// @return true on success
    virtual bool updateMetadata(const std::string& variable_id, const VariableMetadata& metadata) = 0;
    
    /// Start the userfaultfd handler thread and event processing
    /// @return true on success
    virtual bool start() = 0;
    
    /// Pause event processing (drain in-flight events)
    /// @return true on success
    virtual bool pause() = 0;
    
    /// Resume event processing after pause
    /// @return true on success
    virtual bool resume() = 0;
    
    /// Gracefully stop all processing
    /// Drains queue, stops handler, closes uffd
    /// @param timeout_ms Maximum time to wait for draining (default 5000ms)
    /// @return true on success
    virtual bool stop(int timeout_ms = 5000) = 0;
    
    /// Get current core state
    enum State { UNINITIALIZED, INITIALIZED, RUNNING, PAUSED, STOPPED, ERROR };
    virtual State getState() const = 0;
    
    /// Get error message if in ERROR state
    virtual std::string getErrorMessage() const = 0;
    
    /// Dequeue next enriched event (for slow-path processing)
    /// Non-blocking; returns nullptr if queue is empty
    /// @return Pointer to EnrichedEvent, or nullptr
    virtual EnrichedEvent* dequeueEvent() = 0;
    
    /// Get metrics snapshot for observability
    struct Metrics {
        uint64_t events_received;
        uint64_t events_processed;
        uint64_t events_dropped;
        uint64_t callbacks_failed;
        double mean_latency_ms;
        uint32_t queue_depth;
    };
    virtual Metrics getMetrics() const = 0;
    
    virtual ~WatcherCore() = default;

protected:
    WatcherCore() = default;

private:
    WatcherCore(const WatcherCore&) = delete;
    WatcherCore& operator=(const WatcherCore&) = delete;
};

}  // namespace watcher
