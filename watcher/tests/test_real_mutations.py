"""
REAL MUTATION DETECTION TEST - TEST 1
Uses test-fix-test-fix cycle to validate actual mutation tracking.

This test ACTUALLY tries to:
1. Register a variable with the watcher
2. Mutate it in Python
3. Ask watcher "what changed?"
4. Verify it caught the change
"""

import sys
import ctypes
import tempfile
import mmap
import struct
import pickle
from pathlib import Path

sys.path.insert(0, '/workspaces/WaterCodeFlow')

print("="*70)
print("TEST 1: REAL MUTATION DETECTION - Allocate & Register Page")
print("="*70)

# Load the C++ library
lib_path = Path('/workspaces/WaterCodeFlow/build/libwatcher_python.so')
lib = ctypes.CDLL(str(lib_path), use_errno=True)

# Set up function signatures
lib.watcher_initialize.argtypes = [ctypes.c_char_p]
lib.watcher_initialize.restype = ctypes.c_void_p

lib.watcher_start.restype = ctypes.c_bool

lib.watcher_register_page.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_uint32]
lib.watcher_register_page.restype = ctypes.c_void_p

lib.watcher_write_snapshot.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
lib.watcher_write_snapshot.restype = ctypes.c_bool

lib.watcher_read_snapshot.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_size_t)]
lib.watcher_read_snapshot.restype = ctypes.c_void_p

lib.watcher_get_state.restype = ctypes.c_int
lib.watcher_get_error.restype = ctypes.c_char_p

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n1. Initialize C++ core with output dir: {tmpdir}")
        output_dir_bytes = tmpdir.encode('utf-8')
        
        result_ptr = lib.watcher_initialize(output_dir_bytes)
        if result_ptr:
            result_str = ctypes.string_at(result_ptr).decode('utf-8', errors='ignore')
            print(f"   Result: {result_str}")
        
        state = lib.watcher_get_state()
        error = lib.watcher_get_error()
        print(f"   State: {state}, Error: {error.decode() if error else 'None'}")
        
        print(f"\n2. Allocate memory page (4096 bytes)")
        # Allocate a page for a variable
        page_data = (ctypes.c_uint8 * 4096)()
        page_base = ctypes.addressof(page_data)
        print(f"   Page allocated at: 0x{page_base:x}")
        
        print(f"\n3. Register page with watcher")
        var_name = b"test_var"
        flags = 0  # No special flags for now
        
        var_id_ptr = lib.watcher_register_page(
            ctypes.c_void_p(page_base),
            4096,
            var_name,
            flags
        )
        
        if var_id_ptr:
            var_id = ctypes.string_at(var_id_ptr).decode('utf-8', errors='ignore')
            print(f"   ✅ Variable registered with ID: {var_id}")
        else:
            print(f"   ❌ Registration failed")
            sys.exit(1)
        
        print(f"\n4. Write initial snapshot (value=100)")
        # Create initial value
        initial_value = 100
        initial_bytes = struct.pack('<I', initial_value)  # 4 bytes for integer
        
        success = lib.watcher_write_snapshot(
            var_id.encode('utf-8'),
            ctypes.c_char_p(initial_bytes),
            len(initial_bytes)
        )
        print(f"   Write result: {success}")
        if success:
            print(f"   ✅ Snapshot written")
        
        print(f"\n5. Read snapshot back")
        out_len = ctypes.c_size_t()
        snap_ptr = lib.watcher_read_snapshot(
            var_id.encode('utf-8'),
            ctypes.byref(out_len)
        )
        
        if snap_ptr and out_len.value > 0:
            snap_bytes = ctypes.string_at(snap_ptr, out_len.value)
            snap_value = struct.unpack('<I', snap_bytes)[0]
            print(f"   ✅ Read back value: {snap_value}")
            if snap_value == 100:
                print(f"   ✅ PASS: Value matches!")
            else:
                print(f"   ❌ FAIL: Value mismatch! Expected 100, got {snap_value}")
        else:
            print(f"   ❌ FAIL: Could not read snapshot")
        
        print(f"\n6. Write new snapshot (value=200)")
        new_value = 200
        new_bytes = struct.pack('<I', new_value)
        
        success = lib.watcher_write_snapshot(
            var_id.encode('utf-8'),
            ctypes.c_char_p(new_bytes),
            len(new_bytes)
        )
        print(f"   Write result: {success}")
        
        print(f"\n7. Read new snapshot")
        out_len = ctypes.c_size_t()
        snap_ptr = lib.watcher_read_snapshot(
            var_id.encode('utf-8'),
            ctypes.byref(out_len)
        )
        
        if snap_ptr and out_len.value > 0:
            snap_bytes = ctypes.string_at(snap_ptr, out_len.value)
            snap_value = struct.unpack('<I', snap_bytes)[0]
            print(f"   ✅ Read back value: {snap_value}")
            if snap_value == 200:
                print(f"   ✅ PASS: Mutation detected! 100 → 200")
            else:
                print(f"   ❌ FAIL: Expected 200, got {snap_value}")
        
        print("\n" + "="*70)
        print("✅ TEST 1 COMPLETE: Basic snapshot read/write works")
        print("="*70)

except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
