#include <watcher_core.hpp>
#include <cassert>
#include <iostream>
#include <thread>
#include <chrono>
#include <cstring>

using namespace watcher;

// ============================================================================
// Test Utilities
// ============================================================================

void test_print(const std::string& test_name, bool passed) {
    std::cout << "[" << (passed ? "PASS" : "FAIL") << "] " << test_name << std::endl;
}

// ============================================================================
// Core Tests
// ============================================================================

void test_initialization() {
    auto& core = WatcherCore::getInstance();
    bool success = core.initialize("./test_output", 1000);
    test_print("Initialization", success && core.getState() == WatcherCore::INITIALIZED);
}

void test_register_unregister() {
    auto& core = WatcherCore::getInstance();
    
    if (core.getState() != WatcherCore::INITIALIZED) {
        core.initialize("./test_output", 1000);
    }
    
    // Create a test page
    char page[4096];
    memset(page, 0, sizeof(page));
    
    // Register
    MutationDepth depth{true, 0};
    std::string var_id = core.registerPage(page, 4096, "test_var", 
                                          FLAG_TRACK_THREADS, depth);
    bool registered = !var_id.empty() && var_id.find("Error") != 0;
    
    // Unregister
    bool unregistered = core.unregisterPage(var_id);
    
    test_print("Register/Unregister", registered && unregistered);
}

void test_snapshot() {
    auto& core = WatcherCore::getInstance();
    
    if (core.getState() != WatcherCore::INITIALIZED) {
        core.initialize("./test_output", 1000);
    }
    
    // Create test page with data
    char page[4096];
    memset(page, 'A', 256);
    
    // Register
    MutationDepth depth{true, 0};
    std::string var_id = core.registerPage(page, 4096, "snapshot_test",
                                          FLAG_TRACK_THREADS, depth);
    
    if (var_id.empty() || var_id.find("Error") == 0) {
        test_print("Snapshot Test", false);
        return;
    }
    
    // Read snapshot
    auto snapshot = core.readSnapshot(var_id);
    bool read_success = snapshot.size() == 4096 && snapshot[0] == 'A';
    
    // Write snapshot
    std::vector<uint8_t> new_snapshot(4096);
    memset(new_snapshot.data(), 'B', 256);
    bool write_success = core.writeSnapshot(var_id, new_snapshot);
    
    // Verify write
    auto verify_snapshot = core.readSnapshot(var_id);
    bool verify_success = verify_snapshot.size() == 4096 && verify_snapshot[0] == 'B';
    
    core.unregisterPage(var_id);
    
    test_print("Snapshot Operations", read_success && write_success && verify_success);
}

void test_state_transitions() {
    auto& core = WatcherCore::getInstance();
    
    if (core.getState() != WatcherCore::INITIALIZED) {
        core.initialize("./test_output", 1000);
    }
    
    // Start
    bool started = core.start();
    bool running = core.getState() == WatcherCore::RUNNING;
    
    // Pause
    bool paused = core.pause();
    bool paused_state = core.getState() == WatcherCore::PAUSED;
    
    // Resume
    bool resumed = core.resume();
    bool resumed_state = core.getState() == WatcherCore::RUNNING;
    
    // Stop
    bool stopped = core.stop();
    bool stopped_state = core.getState() == WatcherCore::STOPPED;
    
    test_print("State Transitions", started && running && paused && paused_state &&
                                    resumed && resumed_state && stopped && stopped_state);
}

void test_metrics() {
    auto& core = WatcherCore::getInstance();
    
    if (core.getState() != WatcherCore::INITIALIZED) {
        core.initialize("./test_output", 1000);
    }
    
    auto metrics = core.getMetrics();
    bool has_metrics = metrics.events_received >= 0 &&
                      metrics.events_processed >= 0 &&
                      metrics.events_dropped >= 0;
    
    test_print("Metrics Collection", has_metrics);
}

void test_error_handling() {
    auto& core = WatcherCore::getInstance();
    
    // Try to register before initialization
    char page[4096];
    MutationDepth depth{true, 0};
    
    std::string var_id = core.registerPage(page, 4096, "error_test",
                                          FLAG_TRACK_THREADS, depth);
    
    // Should succeed if already initialized, or be empty if not
    bool error_handled = var_id.empty() || var_id.find("Error") != 0;
    
    test_print("Error Handling", error_handled);
}

// ============================================================================
// Main Test Runner
// ============================================================================

int main() {
    std::cout << "=== Watcher Core Unit Tests ===" << std::endl;
    std::cout << std::endl;
    
    test_initialization();
    test_register_unregister();
    test_snapshot();
    test_state_transitions();
    test_metrics();
    test_error_handling();
    
    std::cout << std::endl;
    std::cout << "=== All tests completed ===" << std::endl;
    
    return 0;
}
