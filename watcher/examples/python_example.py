"""
Example Watcher User Script - Python

This demonstrates how to use the Watcher framework to track variable mutations.
Run with: python -m watcher.cli.main --user-script examples/python_example.py --output ./events
"""

# The watch() function is injected by the Watcher CLI
# No import needed - it's available globally

def main():
    """
    Main entry point - automatically called by Watcher CLI
    
    Usage:
        counter = watch(initial_value, name="variable_name", **options)
        # Use counter normally, mutations are tracked
    """
    
    print("=== Watcher Python Example ===\n")
    
    # Example 1: Watch a simple counter
    print("Example 1: Simple Counter")
    counter = watch(0, name="counter")
    
    for i in range(5):
        counter = counter + 1
        print(f"  counter = {counter}")
    
    print()
    
    # Example 2: Watch a list
    print("Example 2: List Mutations")
    items = watch([], name="items")
    
    # Note: Direct list operations need to go through proxy
    # For demo, we'll show the limitation
    print("  [Complex list operations would be tracked]")
    
    print()
    
    # Example 3: Watch a dictionary (as a simple case)
    print("Example 3: Numeric Operations")
    value = watch(100, name="value")
    
    value = value * 2
    print(f"  value * 2 = {value}")
    
    value = value - 50
    print(f"  value - 50 = {value}")
    
    value = value / 2
    print(f"  value / 2 = {value}")
    
    print()
    
    # Example 4: Watch with thread tracking (if enabled)
    print("Example 4: Multi-threaded Mutations")
    shared_state = watch(0, name="shared_state", track_threads=True)
    
    # Sequential mutations (would be tracked with thread ID)
    for i in range(3):
        shared_state = shared_state + 1
        print(f"  Mutation {i+1}: {shared_state}")
    
    print()
    
    # Example 5: Watch with type conversions
    print("Example 5: Type Conversions")
    number = watch(42, name="number")
    
    print(f"  Original: {number} (type: int)")
    print(f"  As float: {float(number)}")
    print(f"  As string: '{str(number)}'")
    
    print()
    print("=== Example Complete ===")
    print("Check ./events directory for event logs in JSONL format")


# This conditional allows the script to be run directly or via CLI
if __name__ == "__main__":
    main()
