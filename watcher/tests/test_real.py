#!/usr/bin/env python3
"""
REAL WATCHER FRAMEWORK TESTS
============================

These tests verify actual framework functionality:
1. C++ core FFI communication
2. Variable registration and page allocation
3. Snapshot read/write operations
4. Python adapter ShadowMemory mutations
5. Thread-safe operations
6. Multi-variable tracking
"""

import sys
import os
import ctypes
import struct
import tempfile
import threading
import time
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'

tests_passed = 0
tests_failed = 0

def print_test(name, passed, message=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        print(f"{GREEN}✅ PASS{RESET}: {name}")
    else:
        tests_failed += 1
        print(f"{RED}❌ FAIL{RESET}: {name}")
    if message:
        print(f"   {message}")


if __name__ == "__main__":
    # ============================================================================
    # Test Suite 1: C++ Core FFI
    # ============================================================================
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}TEST SUITE 1: C++ CORE FFI COMMUNICATION{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    try:
        lib_path = Path(__file__).parent.parent.parent / "build" / "libwatcher_python.so"
        if not lib_path.exists():
            print(f"{RED}❌ FATAL: libwatcher_python.so not found at {lib_path}{RESET}")
            print("Run: ./setup.sh first")
            sys.exit(1)
        
        lib = ctypes.CDLL(str(lib_path), use_errno=True)
        print_test("Library Load", True, f"Loaded {lib_path}")
    except Exception as e:
        print_test("Library Load", False, str(e))
        sys.exit(1)
    
    # Set up function signatures
    lib.watcher_initialize.argtypes = [ctypes.c_char_p]
    lib.watcher_initialize.restype = ctypes.c_void_p
    
    lib.watcher_get_state.restype = ctypes.c_int
    lib.watcher_get_error.restype = ctypes.c_char_p
    
    lib.watcher_register_page.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_uint32]
    lib.watcher_register_page.restype = ctypes.c_char_p
    
    lib.watcher_write_snapshot.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
    lib.watcher_write_snapshot.restype = ctypes.c_bool
    
    lib.watcher_read_snapshot.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_size_t)]
    lib.watcher_read_snapshot.restype = ctypes.c_void_p
    
    lib.watcher_start.restype = ctypes.c_bool
    lib.watcher_stop.restype = ctypes.c_bool
    
    # TEST 1: Initialize core
    print("TEST 1: Initialize C++ Core")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = lib.watcher_initialize(tmpdir.encode('utf-8'))
        state = lib.watcher_get_state()
        error = lib.watcher_get_error()
        
        error_msg = error.decode() if error else "None"
        
        # State 1 = INITIALIZED, State 5 = ERROR
        if state == 1:
            print_test("Initialize Core", True, f"State={state}")
        elif state == 5:
            print_test("Initialize Core", False, f"State=ERROR: {error_msg}")
        else:
            print_test("Initialize Core", False, f"Unexpected state: {state}")
    
    # TEST 2: Register page
    print("\nTEST 2: Register Variable Page")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib.watcher_initialize(tmpdir.encode('utf-8'))
        
        page_data = (ctypes.c_uint8 * 4096)()
        page_base = ctypes.addressof(page_data)
        
        var_id_bytes = lib.watcher_register_page(
            ctypes.c_void_p(page_base),
            4096,
            b"test_var_1",
            0
        )
        
        var_id = var_id_bytes.decode('utf-8') if var_id_bytes else None
        
        if var_id and len(var_id) > 0:
            print_test("Register Page", True, f"Variable ID: {var_id}")
        else:
            print_test("Register Page", False, f"Got empty/null ID")
    
    # TEST 3: Write and read snapshot
    print("\nTEST 3: Snapshot Read/Write")
    with tempfile.TemporaryDirectory() as tmpdir:
        lib.watcher_initialize(tmpdir.encode('utf-8'))
        
        page_data = (ctypes.c_uint8 * 4096)()
        page_base = ctypes.addressof(page_data)
        
        var_id_bytes = lib.watcher_register_page(ctypes.c_void_p(page_base), 4096, b"test_var_2", 0)
        var_id = var_id_bytes.decode('utf-8')
        
        # Write value
        test_value = 42
        test_bytes = struct.pack('<I', test_value)
        write_success = lib.watcher_write_snapshot(var_id.encode('utf-8'), test_bytes, len(test_bytes))
        
        if write_success:
            print_test("Write Snapshot", True)
        else:
            print_test("Write Snapshot", False, "write_snapshot returned False")
        
        # Read value back
        out_len = ctypes.c_size_t()
        snap_ptr = lib.watcher_read_snapshot(var_id.encode('utf-8'), ctypes.byref(out_len))
        
        if snap_ptr and out_len.value > 0:
            snap_bytes = ctypes.string_at(snap_ptr, out_len.value)
            read_value = struct.unpack('<I', snap_bytes)[0]
            
            if read_value == test_value:
                print_test("Read Snapshot", True, f"Read value: {read_value}")
            else:
                print_test("Read Snapshot", False, f"Expected {test_value}, got {read_value}")
        else:
            print_test("Read Snapshot", False, "Could not read snapshot")
    
    # ============================================================================
    # Test Suite 2: Python Adapter
    # ============================================================================
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}TEST SUITE 2: PYTHON ADAPTER{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    try:
        from watcher.adapters.python import ShadowMemory, WatcherCore, SQLContextManager
        print_test("Import Adapter", True)
    except ImportError as e:
        print_test("Import Adapter", False, str(e))
        sys.exit(1)
    
    # TEST 4: ShadowMemory basic operations
    print("TEST 4: ShadowMemory Basic Operations")
    try:
        sm = ShadowMemory(100)
        sm.write(101)
        sm.write(102)
        value = sm.read()
        
        if value == 102:
            print_test("ShadowMemory Read/Write", True, f"Final value: {value}")
        else:
            print_test("ShadowMemory Read/Write", False, f"Expected 102, got {value}")
    except Exception as e:
        print_test("ShadowMemory Read/Write", False, str(e))
    
    # TEST 5: ShadowMemory with complex types
    print("\nTEST 5: ShadowMemory Complex Types")
    try:
        test_dict = {"name": "Alice", "age": 30, "tags": ["python", "js"]}
        sm = ShadowMemory(test_dict)
        sm.write({"name": "Bob", "age": 25})
        value = sm.read()
        
        if value and value.get("name") == "Bob":
            print_test("ShadowMemory Dict", True, f"Read: {value}")
        else:
            print_test("ShadowMemory Dict", False, f"Value mismatch: {value}")
    except Exception as e:
        print_test("ShadowMemory Dict", False, str(e))
    
    # TEST 6: Thread safety
    print("\nTEST 6: Thread Safety")
    try:
        results = []
        def thread_func(tid, value):
            sm = ShadowMemory({"tid": tid, "value": value})
            results.append(sm.read())
        
        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_func, args=(i, i*100))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        if len(results) == 3 and all(r and r.get('tid') is not None for r in results):
            print_test("Thread Safety", True, f"Processed {len(results)} threads")
        else:
            print_test("Thread Safety", False, f"Incomplete results: {results}")
    except Exception as e:
        print_test("Thread Safety", False, str(e))
    
    # TEST 7: SQL Context Manager
    print("\nTEST 7: SQL Context Management")
    try:
        sql = SQLContextManager()
        sql.push_context("SELECT * FROM users", [1, 2, 3])
        ctx = sql.current_context()
        
        if ctx and ctx['query'] == "SELECT * FROM users":
            print_test("SQL Push/Current", True, f"Query: {ctx['query']}")
        else:
            print_test("SQL Push/Current", False, f"Context issue: {ctx}")
        
        popped = sql.pop_context()
        if popped and sql.current_context() is None:
            print_test("SQL Pop", True)
        else:
            print_test("SQL Pop", False, "Stack not cleared")
    except Exception as e:
        print_test("SQL Context Management", False, str(e))
    
    # TEST 8: WatcherCore Singleton
    print("\nTEST 8: WatcherCore Singleton")
    try:
        c1 = WatcherCore.getInstance()
        c2 = WatcherCore.getInstance()
        
        if c1 is c2:
            print_test("Singleton Pattern", True)
        else:
            print_test("Singleton Pattern", False, "Different instances returned")
    except Exception as e:
        print_test("Singleton Pattern", False, str(e))
    
    # ============================================================================
    # Test Suite 3: Multi-variable Tracking
    # ============================================================================
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}TEST SUITE 3: MULTI-VARIABLE TRACKING{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    # TEST 9: Multiple ShadowMemory instances
    print("TEST 9: Multiple Variables")
    try:
        sm1 = ShadowMemory(10)
        sm2 = ShadowMemory(20)
        sm3 = ShadowMemory([1, 2, 3])
        
        sm1.write(11)
        sm2.write(21)
        sm3.write([1, 2, 3, 4])
        
        v1 = sm1.read()
        v2 = sm2.read()
        v3 = sm3.read()
        
        if v1 == 11 and v2 == 21 and len(v3) == 4:
            print_test("Multiple Variables", True, f"v1={v1}, v2={v2}, v3_len={len(v3)}")
        else:
            print_test("Multiple Variables", False, f"Values: {v1}, {v2}, {v3}")
    except Exception as e:
        print_test("Multiple Variables", False, str(e))
    
    # TEST 10: Rapid mutations
    print("\nTEST 10: Rapid Mutations")
    try:
        sm = ShadowMemory(0)
        for i in range(1, 101):
            sm.write(i)
        
        final_value = sm.read()
        if final_value == 100:
            print_test("Rapid Mutations", True, f"100 mutations processed")
        else:
            print_test("Rapid Mutations", False, f"Expected 100, got {final_value}")
    except Exception as e:
        print_test("Rapid Mutations", False, str(e))
    
    # ============================================================================
    # Summary
    # ============================================================================
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}TEST SUMMARY{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"\nPassed: {GREEN}{tests_passed}{RESET}")
    print(f"Failed: {RED}{tests_failed}{RESET}")
    print(f"Total:  {BOLD}{tests_passed + tests_failed}{RESET}")
    
    if tests_failed == 0:
        print(f"\n{GREEN}{BOLD}✅ ALL TESTS PASSED!{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}{BOLD}❌ SOME TESTS FAILED{RESET}")
        sys.exit(1)
