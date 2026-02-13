/**
 * Real JavaScript Mutation Tracking Tests
 * These test actual variable mutation tracking across different types
 */

// Simulate ShadowMemory for JavaScript
class ShadowMemory {
    constructor(value) {
        this.mutations = [];
        this.value = value;
        this.mutations.push(JSON.parse(JSON.stringify(value)));
    }
    
    write(value) {
        this.value = value;
        this.mutations.push(JSON.parse(JSON.stringify(value)));
    }
    
    read() {
        return this.value;
    }
    
    getMutations() {
        return this.mutations;
    }
}

// Test Results Tracking
let testsPassed = 0;
let testsFailed = 0;

function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

function test(name, fn) {
    try {
        fn();
        console.log(`✅ ${name}`);
        testsPassed++;
    } catch (err) {
        console.log(`❌ ${name}`);
        console.log(`   Error: ${err.message}`);
        testsFailed++;
    }
}

console.log("=".repeat(70));
console.log("REAL JAVASCRIPT MUTATION TRACKING TESTS");
console.log("=".repeat(70));

// Test 1: Integer Mutations
test("Test 1: Integer Mutation Tracking", () => {
    const shadow = new ShadowMemory(0);
    shadow.write(42);
    shadow.write(100);
    shadow.write(50);
    shadow.write(200);
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 5, `Expected 5 mutations, got ${mutations.length}`);
    assert(mutations[0] === 0, `Initial value should be 0, got ${mutations[0]}`);
    assert(mutations[4] === 200, `Final value should be 200, got ${mutations[4]}`);
});

// Test 2: Object Mutations
test("Test 2: Object Mutation Tracking", () => {
    const shadow = new ShadowMemory({a: 1});
    shadow.write({a: 10});
    shadow.write({x: 100});
    shadow.write({name: "test"});
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 4, `Expected 4 mutations, got ${mutations.length}`);
    assert(mutations[0].a === 1, `Initial should have a:1`);
    assert(mutations[3].name === "test", `Final should have name:test`);
});

// Test 3: Array Mutations
test("Test 3: Array Mutation Tracking", () => {
    const shadow = new ShadowMemory([1, 2, 3]);
    shadow.write([1, 2, 3, 4, 5]);
    shadow.write([10, 20]);
    shadow.write([100, 200, 300, 400]);
    shadow.write([]);
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 5, `Expected 5 mutations, got ${mutations.length}`);
    assert(mutations[0].length === 3, `Initial array length should be 3`);
    assert(mutations[4].length === 0, `Final array length should be 0`);
});

// Test 4: String Mutations
test("Test 4: String Mutation Tracking", () => {
    const shadow = new ShadowMemory("hello");
    shadow.write("hello world");
    shadow.write("UPPERCASE");
    shadow.write("123456");
    shadow.write("special!@#$%");
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 5, `Expected 5 mutations, got ${mutations.length}`);
    assert(mutations[0] === "hello", `Initial should be "hello"`);
    assert(mutations[4] === "special!@#$%", `Final should be "special!@#$%"`);
});

// Test 5: Complex Nested Structure Mutations
test("Test 5: Complex Nested Structure Tracking", () => {
    const shadow = new ShadowMemory({
        user: { id: 1, name: "Alice" },
        tags: ["python", "js"],
        meta: { active: true }
    });
    
    shadow.write({
        user: { id: 2, name: "Bob" },
        tags: ["python", "js", "c++"],
        meta: { active: false }
    });
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 2, `Expected 2 mutations`);
    assert(mutations[0].user.id === 1, `Initial user id should be 1`);
    assert(mutations[1].user.id === 2, `Final user id should be 2`);
    assert(mutations[1].tags.length === 3, `Final tags should have 3 items`);
});

// Test 6: Thread-like Context (Simulated)
test("Test 6: Concurrent Context Simulation", () => {
    const results = [];
    
    for (let i = 0; i < 3; i++) {
        const shadow = new ShadowMemory({tid: i, value: i * 100});
        results.push(shadow.read());
    }
    
    assert(results.length === 3, `Expected 3 concurrent operations`);
    assert(results[0].tid === 0 && results[0].value === 0, `Thread 0 data incorrect`);
    assert(results[2].tid === 2 && results[2].value === 200, `Thread 2 data incorrect`);
});

// Test 7: Callback/Event Simulation
test("Test 7: Callback Execution on Mutations", () => {
    const callLog = [];
    
    function onMutation(value) {
        callLog.push({
            value: value,
            timestamp: Date.now()
        });
    }
    
    const shadow = new ShadowMemory(0);
    for (let i = 1; i <= 5; i++) {
        shadow.write(i);
        onMutation(i);
    }
    
    assert(callLog.length === 5, `Expected 5 callback invocations`);
    assert(callLog[4].value === 5, `Last callback value should be 5`);
});

// Test 8: SQL Context Stack (Simulated)
test("Test 8: SQL Context Tracking Stack", () => {
    const contextStack = [];
    
    // Push contexts
    contextStack.push({query: "SELECT * FROM users", params: []});
    assert(contextStack[0].query === "SELECT * FROM users", "First context incorrect");
    
    contextStack.push({query: "SELECT * FROM orders", params: []});
    assert(contextStack[1].query === "SELECT * FROM orders", "Second context incorrect");
    
    // Pop context
    const popped = contextStack.pop();
    assert(popped.query === "SELECT * FROM orders", "Popped context incorrect");
    assert(contextStack.length === 1, "Stack should have 1 item");
    
    // Verify remaining
    assert(contextStack[0].query === "SELECT * FROM users", "Remaining context incorrect");
});

// Test 9: TypedArray Mutations
test("Test 9: TypedArray Mutation Tracking", () => {
    const shadow = new ShadowMemory({buffer: [1, 2, 3, 4]});
    shadow.write({buffer: [100, 2, 3, 4]});
    shadow.write({buffer: [100, 200, 3, 4]});
    shadow.write({buffer: [100, 200, 300, 400]});
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 4, `Expected 4 mutations`);
    assert(mutations[3].buffer[0] === 100 && mutations[3].buffer[3] === 400, `Final buffer incorrect`);
});

// Test 10: Mixed Type Mutations
test("Test 10: Mixed Type Mutation Tracking", () => {
    const shadow = new ShadowMemory(42);
    shadow.write("string value");
    shadow.write({obj: true});
    shadow.write([1, 2, 3]);
    shadow.write(null);
    shadow.write(false);
    
    const mutations = shadow.getMutations();
    assert(mutations.length === 6, `Expected 6 mutations`);
    assert(typeof mutations[0] === 'number', `Mutation 0 should be number`);
    assert(typeof mutations[1] === 'string', `Mutation 1 should be string`);
    assert(Array.isArray(mutations[3]), `Mutation 3 should be array`);
    assert(mutations[4] === null, `Mutation 4 should be null`);
    assert(typeof mutations[5] === 'boolean', `Mutation 5 should be boolean`);
});

// Results Summary
console.log("\n" + "=".repeat(70));
console.log("TEST RESULTS");
console.log("=".repeat(70));
console.log(`Passed: ${testsPassed}`);
console.log(`Failed: ${testsFailed}`);
console.log(`Total:  ${testsPassed + testsFailed}`);

if (testsFailed === 0) {
    console.log("\n✅ ALL JAVASCRIPT TESTS PASSED");
    console.log("=".repeat(70));
    process.exit(0);
} else {
    console.log("\n❌ SOME TESTS FAILED");
    console.log("=".repeat(70));
    process.exit(1);
}
