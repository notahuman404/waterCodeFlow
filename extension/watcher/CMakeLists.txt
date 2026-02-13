cmake_minimum_required(VERSION 3.16)
project(WatcherFramework CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================================================
# Core Library
# ============================================================================

add_library(watcher_core SHARED
    core/src/watcher_core.cpp
)

target_include_directories(watcher_core 
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/core/include
)

target_link_libraries(watcher_core
    pthread
)

# ============================================================================
# Python Adapter
# ============================================================================

add_library(watcher_python SHARED
    adapters/python/adapter.cpp
)

target_include_directories(watcher_python
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/core/include
    PRIVATE ${PYTHON_INCLUDE_DIRS}
)

target_link_libraries(watcher_python
    watcher_core
    ${PYTHON_LIBRARIES}
)

# ============================================================================
# JavaScript/N-API Adapter
# ============================================================================

# Skipped for now - requires node-addon-api npm package and node headers
# Will be built separately as native Node.js module
# add_library(watcher_js SHARED
#     watcher/adapters/javascript/adapter.cpp
# )

# ============================================================================
# Custom Processor
# ============================================================================

add_library(watcher_processor SHARED
    processor/processor.cpp
)

target_include_directories(watcher_processor
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/processor/include
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/core/include
)

target_link_libraries(watcher_processor
    watcher_core
    pthread
)

# ============================================================================
# Tests
# ============================================================================

enable_testing()

add_executable(test_core
    tests/test_core.cpp
)

target_link_libraries(test_core
    watcher_core
)

add_test(NAME CoreTests COMMAND test_core)
