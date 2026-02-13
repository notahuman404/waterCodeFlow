#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>

namespace watcher::python {

// FFI interface to C++ core
extern "C" {
    // Core initialization
    const char* watcher_initialize(const char* output_dir);
    bool watcher_start();
    bool watcher_stop();

    // Variable registration
    const char* watcher_register_page(void* page_base, size_t page_size,
                                      const char* name, uint32_t flags);
    bool watcher_unregister_page(const char* variable_id);

    // Snapshot operations
    void* watcher_read_snapshot(const char* variable_id, size_t* out_len);
    bool watcher_write_snapshot(const char* variable_id, void* data, size_t len);

    // Event dequeuing (Phase 3)
    // Get next fast-path event as JSON string
    // Returns JSON string, or empty string if queue is empty
    // Caller must free the returned pointer with free()
    const char* watcher_dequeue_fast_path_event();

    // State queries
    int watcher_get_state();
    const char* watcher_get_error();
}

}  // namespace watcher::python
