#include "watcher_core.hpp"
#include <string>
#include <vector>
#include <cstdint>
#include <sstream>
#include <iomanip>

extern "C" {

const char* watcher_initialize(const char* output_dir) {
    static thread_local std::string result;
    auto& core = watcher::WatcherCore::getInstance();
    if (core.initialize(output_dir)) {
        result = "OK";
        return result.c_str();
    }
    result = core.getErrorMessage();
    return result.c_str();
}

bool watcher_start() {
    return watcher::WatcherCore::getInstance().start();
}

bool watcher_stop() {
    return watcher::WatcherCore::getInstance().stop();
}

const char* watcher_register_page(void* page_base, size_t page_size,
                                  const char* name, uint32_t flags) {
    static thread_local std::string last_id;

    watcher::MutationDepth depth{true, 0};
    last_id = watcher::WatcherCore::getInstance().registerPage(
        page_base, page_size, name, static_cast<watcher::EventFlags>(flags), depth
    );

    if (last_id.empty()) {
        last_id = "Error: page registration failed";
    }
    return last_id.c_str();
}

bool watcher_unregister_page(const char* variable_id) {
    return watcher::WatcherCore::getInstance().unregisterPage(variable_id);
}

void* watcher_read_snapshot(const char* variable_id, size_t* out_len) {
    static thread_local std::vector<uint8_t> snapshot;
    snapshot = watcher::WatcherCore::getInstance().readSnapshot(variable_id);
    *out_len = snapshot.size();
    return snapshot.data();
}

bool watcher_write_snapshot(const char* variable_id, void* data, size_t len) {
    std::vector<uint8_t> snapshot(static_cast<uint8_t*>(data),
                                   static_cast<uint8_t*>(data) + len);
    return watcher::WatcherCore::getInstance().writeSnapshot(variable_id, snapshot);
}

// Phase 3: Event dequeuing
const char* watcher_dequeue_fast_path_event() {
    static thread_local std::string event_json;

    auto event = watcher::WatcherCore::getInstance().dequeueEvent();
    if (!event) {
        event_json = "";
        return event_json.c_str();
    }

    // Serialize to JSON format (minimal representation)
    std::ostringstream oss;
    oss << "{"
        << "\"event_id\":\"" << event->event_id << "\","
        << "\"timestamp_ns\":" << event->ts_ns << ","
        << "\"ip\":" << event->ip << ","
        << "\"tid\":" << event->tid << ","
        << "\"page_base\":\"0x" << std::hex << reinterpret_cast<uintptr_t>(event->page_base) << std::dec << "\""
        << "}";

    event_json = oss.str();
    return event_json.c_str();
}

int watcher_get_state() {
    return static_cast<int>(watcher::WatcherCore::getInstance().getState());
}

const char* watcher_get_error() {
    static thread_local std::string error;
    error = watcher::WatcherCore::getInstance().getErrorMessage();
    return error.c_str();
}

}  // extern "C"
