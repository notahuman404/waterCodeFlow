/**
 * Basic JavaScript user script for testing
 */

function main() {
    console.log("Hello from JavaScript!");
    
    // Test that watch is available in global scope
    if (typeof global.watch === 'function') {
        console.log("Watch function is available!");
    } else {
        throw new Error("Watch function not found in global scope");
    }
    
    return 42;
}

// Export main for Node.js
module.exports = { main };
