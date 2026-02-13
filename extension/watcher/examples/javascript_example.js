/**
 * Example Watcher User Script - JavaScript
 * 
 * This demonstrates how to use the Watcher framework to track TypedArray mutations.
 * Run with: node -e "require('./examples/javascript_example.js').main()"
 */

const { watch } = require('../watcher/adapters/javascript');

async function main() {
    console.log("=== Watcher JavaScript Example ===\n");
    
    // Example 1: Watch a Uint32Array
    console.log("Example 1: Uint32Array Mutations");
    const counter = new Uint32Array(1);
    counter[0] = 0;
    watch(counter, { name: "counter", trackThreads: false });
    
    for (let i = 0; i < 5; i++) {
        counter[0]++;
        console.log(`  counter[0] = ${counter[0]}`);
    }
    
    console.log();
    
    // Example 2: Watch a Float32Array
    console.log("Example 2: Float32Array Mutations");
    const values = new Float32Array(3);
    values[0] = 1.5;
    values[1] = 2.5;
    values[2] = 3.5;
    watch(values, { name: "values", trackThreads: false });
    
    values[0] = values[0] * 2;
    console.log(`  values[0] *= 2 = ${values[0]}`);
    
    values[1] = values[1] + 1.0;
    console.log(`  values[1] += 1 = ${values[1]}`);
    
    console.log();
    
    // Example 3: Watch with thread tracking
    console.log("Example 3: Multi-threaded Context (Simulated)");
    const state = new Uint8Array(1);
    state[0] = 0;
    watch(state, { name: "state", trackThreads: true });
    
    for (let i = 0; i < 3; i++) {
        state[0]++;
        console.log(`  Mutation ${i + 1}: ${state[0]}`);
    }
    
    console.log();
    
    // Example 4: Watch multiple buffers
    console.log("Example 4: Multiple Buffers");
    const buffers = {
        a: new Uint32Array(1),
        b: new Uint32Array(1),
        c: new Uint32Array(1)
    };
    
    buffers.a[0] = 10;
    buffers.b[0] = 20;
    buffers.c[0] = 30;
    
    watch(buffers.a, { name: "buffer_a", trackThreads: false });
    watch(buffers.b, { name: "buffer_b", trackThreads: false });
    watch(buffers.c, { name: "buffer_c", trackThreads: false });
    
    buffers.a[0] += buffers.b[0];
    console.log(`  buffer_a[0] += buffer_b[0] = ${buffers.a[0]}`);
    
    buffers.c[0] = buffers.a[0] + buffers.b[0];
    console.log(`  buffer_c[0] = buffer_a[0] + buffer_b[0] = ${buffers.c[0]}`);
    
    console.log();
    
    // Example 5: Watch with array operations
    console.log("Example 5: Array-like Operations");
    const data = new Uint16Array(10);
    watch(data, { name: "data" });
    
    for (let i = 0; i < 5; i++) {
        data[i] = i * 10;
        console.log(`  data[${i}] = ${data[i]}`);
    }
    
    console.log();
    console.log("=== Example Complete ===");
    console.log("Check ./events directory for event logs in JSONL format");
}

// Export for use as module
module.exports = { main };

// Allow running directly
if (require.main === module) {
    main().catch(console.error);
}
