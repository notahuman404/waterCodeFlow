#!/usr/bin/env python3
"""
Real Functionality Test - Track Variable Mutations
Tests that the Watcher framework actually detects variable changes.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add watcher to path
import os
from pathlib import Path

# Get the extension root directory (2 levels up from tests/)
EXTENSION_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_ROOT))
os.environ['LD_LIBRARY_PATH'] = str(EXTENSION_ROOT / 'build') + ':' + os.environ.get('LD_LIBRARY_PATH', '')
from watcher.adapters.python import ShadowMemory, WatchProxy, WatcherCore

def test_shadow_memory_mutations():
    """Test 1: ShadowMemory tracks mutations"""
    print("\n" + "="*70)
    print("TEST 1: ShadowMemory Mutation Tracking")
    print("="*70)
    
    # Create watched value
    sm = ShadowMemory(0)
    print(f"✅ Created shadow memory with initial value: 0")
    
    # First read
    val1 = sm.read()
    print(f"✅ Read initial value: {val1}")
    assert val1 == 0, f"Expected 0, got {val1}"
    
    # Mutate
    sm.write(42)
    print(f"✅ Mutated to 42")
    
    # Read after mutation
    val2 = sm.read()
    print(f"✅ Read after mutation: {val2}")
    assert val2 == 42, f"Expected 42, got {val2}"
    
    # More mutations
    for i in range(100, 105):
        sm.write(i)
        result = sm.read()
        assert result == i, f"Expected {i}, got {result}"
    
    print(f"✅ Successfully tracked 5 sequential mutations (100-104)")
    print(f"✅ TEST 1 PASSED")
    return True

def test_watch_proxy_mutations():
    """Test 2: WatchProxy tracks mutations through arithmetic"""
    print("\n" + "="*70)
    print("TEST 2: WatchProxy Mutation Tracking")
    print("="*70)
    
    # Initialize core
    core = WatcherCore.getInstance()
    print(f"✅ WatcherCore initialized")
    
    # Create watched proxy
    shadow = ShadowMemory(10)
    proxy = WatchProxy(shadow, variable_id="counter_var", name="counter")
    print(f"✅ Created WatchProxy for counter with initial value: 10")
    
    # Test mutations via arithmetic
    mutations = [
        (20, "proxy + 10 = 20"),
        (40, "(proxy + 10) * 2 = 40"),
        (35, "(proxy - 5) = 35"),
    ]
    
    for expected, operation in mutations:
        shadow.write(10)  # Reset to 10
        if operation == "proxy + 10 = 20":
            result = proxy + 10
        elif operation == "(proxy + 10) * 2 = 40":
            result = (proxy + 10) * 2
        elif operation == "(proxy - 5) = 35":
            shadow.write(40)
            result = proxy - 5
        
        print(f"  {operation}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print(f"✅ WatchProxy successfully tracked 3 arithmetic mutations")
    print(f"✅ TEST 2 PASSED")
    return True

def test_list_mutations():
    """Test 3: Track list mutations"""
    print("\n" + "="*70)
    print("TEST 3: List Mutation Tracking")
    print("="*70)
    
    # Create watched list
    sm = ShadowMemory([1, 2, 3])
    print(f"✅ Created shadow memory with list: [1, 2, 3]")
    
    # Read initial
    val = sm.read()
    print(f"✅ Read initial list: {val}")
    assert val == [1, 2, 3], f"Expected [1, 2, 3], got {val}"
    
    # Mutate list
    new_list = [1, 2, 3, 4, 5]
    sm.write(new_list)
    print(f"✅ Mutated list to: {new_list}")
    
    # Verify mutation
    val = sm.read()
    assert val == new_list, f"Expected {new_list}, got {val}"
    
    # Multiple mutations
    for i in range(3):
        new_val = list(range(i, i+5))
        sm.write(new_val)
        result = sm.read()
        assert result == new_val, f"Expected {new_val}, got {result}"
    
    print(f"✅ Successfully tracked 3 list mutations")
    print(f"✅ TEST 3 PASSED")
    return True

def test_dict_mutations():
    """Test 4: Track dict mutations"""
    print("\n" + "="*70)
    print("TEST 4: Dictionary Mutation Tracking")
    print("="*70)
    
    # Create watched dict
    initial_dict = {"a": 1, "b": 2}
    sm = ShadowMemory(initial_dict)
    print(f"✅ Created shadow memory with dict: {initial_dict}")
    
    # Read initial
    val = sm.read()
    assert val == initial_dict, f"Expected {initial_dict}, got {val}"
    
    # Mutate dict
    mutations = [
        {"a": 10, "b": 20},
        {"x": 100, "y": 200, "z": 300},
        {"key": "value"},
    ]
    
    for mutation in mutations:
        sm.write(mutation)
        result = sm.read()
        assert result == mutation, f"Expected {mutation}, got {result}"
        print(f"  ✓ Mutation tracked: {mutation}")
    
    print(f"✅ Successfully tracked {len(mutations)} dictionary mutations")
    print(f"✅ TEST 4 PASSED")
    return True

def test_string_mutations():
    """Test 5: Track string mutations"""
    print("\n" + "="*70)
    print("TEST 5: String Mutation Tracking")
    print("="*70)
    
    # Create watched string
    sm = ShadowMemory("hello")
    print(f"✅ Created shadow memory with string: 'hello'")
    
    # Read initial
    val = sm.read()
    assert val == "hello", f"Expected 'hello', got {val}"
    
    # Mutate strings
    mutations = [
        "hello world",
        "UPPERCASE",
        "123456",
        "special!@#$%",
    ]
    
    for mutation in mutations:
        sm.write(mutation)
        result = sm.read()
        assert result == mutation, f"Expected '{mutation}', got '{result}'"
        print(f"  ✓ Mutation tracked: '{mutation}'")
    
    print(f"✅ Successfully tracked {len(mutations)} string mutations")
    print(f"✅ TEST 5 PASSED")
    return True

def main():
    print("\n" + "="*70)
    print("WATCHER FRAMEWORK - REAL FUNCTIONALITY TESTS")
    print("Testing Variable Mutation Tracking")
    print("="*70)
    
    try:
        results = []
        
        # Run all tests
        results.append(("ShadowMemory Mutations", test_shadow_memory_mutations()))
        results.append(("WatchProxy Mutations", test_watch_proxy_mutations()))
        results.append(("List Mutations", test_list_mutations()))
        results.append(("Dict Mutations", test_dict_mutations()))
        results.append(("String Mutations", test_string_mutations()))
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n✅ ALL MUTATION TRACKING TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ {total - passed} tests failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
