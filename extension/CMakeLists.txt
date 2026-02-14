cmake_minimum_required(VERSION 3.16)
project(WaterCodeFlow CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Optimization flags
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")
set(CMAKE_C_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")

# Find Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

message(STATUS "Python3 found: ${Python3_EXECUTABLE}")
message(STATUS "Python3 include: ${Python3_INCLUDE_DIRS}")
message(STATUS "Python3 libraries: ${Python3_LIBRARIES}")

# ============================================================================
# STORAGE UTILITY - Pure C Fast Storage Library
# ============================================================================

add_library(faststorage_c SHARED
    storage_utility/faststorage.c
)

target_compile_options(faststorage_c PRIVATE
    -Wall -Wextra -O3 -march=native
    -fPIC
    $<$<CONFIG:Release>:-DNDEBUG>
)

target_link_libraries(faststorage_c
    pthread
)

set_target_properties(faststorage_c PROPERTIES
    PREFIX ""
    SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# Copy to storage_utility after build
add_custom_command(TARGET faststorage_c POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_BINARY_DIR}/faststorage_c.so
        ${CMAKE_SOURCE_DIR}/storage_utility/faststorage_c.so
    COMMENT "Copying faststorage_c.so to storage_utility/"
)

# ============================================================================
# WATCHER FRAMEWORK - Core Library
# ============================================================================

add_library(watcher_core SHARED
    watcher/core/src/watcher_core.cpp
)

target_include_directories(watcher_core 
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/watcher/core/include
)

target_compile_options(watcher_core PRIVATE
    -Wall -Wextra -O3
    $<$<CONFIG:Release>:-DNDEBUG>
)

target_link_libraries(watcher_core
    pthread
)

set_target_properties(watcher_core PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# ============================================================================
# WATCHER FRAMEWORK - Python Adapter
# ============================================================================

add_library(watcher_python SHARED
    watcher/adapters/python/adapter.cpp
)

target_include_directories(watcher_python
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/watcher/core/include
    PRIVATE ${Python3_INCLUDE_DIRS}
)

target_compile_options(watcher_python PRIVATE
    -Wall -Wextra -O3
    $<$<CONFIG:Release>:-DNDEBUG>
)

target_link_libraries(watcher_python
    watcher_core
    ${Python3_LIBRARIES}
    pthread
)

# Keep the lib prefix and output to build directory
set_target_properties(watcher_python PROPERTIES
    PREFIX "lib"
    SUFFIX ".so"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# No need to copy - Python will import from build/ directly
add_custom_command(TARGET watcher_python POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "✓ libwatcher_python.so is ready in build/"
)

# ============================================================================
# WATCHER FRAMEWORK - Custom Processor
# ============================================================================

add_library(watcher_processor SHARED
    watcher/processor/processor.cpp
)

target_include_directories(watcher_processor
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/watcher/processor/include
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/watcher/core/include
)

target_compile_options(watcher_processor PRIVATE
    -Wall -Wextra -O3
    $<$<CONFIG:Release>:-DNDEBUG>
)

target_link_libraries(watcher_processor
    watcher_core
    pthread
)

set_target_properties(watcher_processor PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# ============================================================================
# WATCHER FRAMEWORK - Storage Utility (duplicate in watcher)
# ============================================================================

# Check if watcher has its own storage_utility
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/watcher/storage_utility/faststorage.c")
    add_library(watcher_faststorage_c SHARED
        watcher/storage_utility/faststorage.c
    )

    target_compile_options(watcher_faststorage_c PRIVATE
        -Wall -Wextra -O3 -march=native
        -fPIC
        $<$<CONFIG:Release>:-DNDEBUG>
    )

    target_link_libraries(watcher_faststorage_c
        pthread
    )

    set_target_properties(watcher_faststorage_c PROPERTIES
        PREFIX ""
        SUFFIX ".so"
        OUTPUT_NAME "faststorage_c"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/watcher_storage"
    )
    
    # Copy to watcher/storage_utility after build
    add_custom_command(TARGET watcher_faststorage_c POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
            ${CMAKE_BINARY_DIR}/watcher_storage/faststorage_c.so
            ${CMAKE_SOURCE_DIR}/watcher/storage_utility/faststorage_c.so
        COMMENT "Copying faststorage_c.so to watcher/storage_utility/"
    )
endif()

# ============================================================================
# TESTS - Core Watcher Tests
# ============================================================================

enable_testing()

add_executable(test_core
    watcher/tests/test_core.cpp
)

target_include_directories(test_core
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/watcher/core/include
)

target_link_libraries(test_core
    watcher_core
)

set_target_properties(test_core PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

add_test(NAME CoreTests COMMAND test_core)

# ============================================================================
# SUMMARY
# ============================================================================

message(STATUS "")
message(STATUS "=================================================")
message(STATUS "WaterCodeFlow Extension - Build Configuration")
message(STATUS "=================================================")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C Compiler: ${CMAKE_C_COMPILER}")
message(STATUS "C++ Compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "")
message(STATUS "Components to build:")
message(STATUS "  ✓ faststorage_c.so (Pure C storage engine)")
message(STATUS "  ✓ watcher_core (C++ watcher framework)")
message(STATUS "  ✓ watcher_python (Python bindings)")
message(STATUS "  ✓ watcher_processor (Custom processor)")
message(STATUS "  ✓ test_core (Unit tests)")
message(STATUS "")
message(STATUS "Python Configuration:")
message(STATUS "  Interpreter: ${Python3_EXECUTABLE}")
message(STATUS "  Version: ${Python3_VERSION}")
message(STATUS "  Include: ${Python3_INCLUDE_DIRS}")
message(STATUS "")
message(STATUS "Build output → ${CMAKE_BINARY_DIR}/")
message(STATUS "")
message(STATUS "Auto-copy after build:")
message(STATUS "  - faststorage_c.so → storage_utility/")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/watcher/storage_utility/faststorage.c")
    message(STATUS "  - faststorage_c.so → watcher/storage_utility/")
endif()
message(STATUS "  - libwatcher_python.so stays in build/")
message(STATUS "")
message(STATUS "Note: Run 'make' only - no need for 'make install'")
message(STATUS "=================================================")
message(STATUS "")