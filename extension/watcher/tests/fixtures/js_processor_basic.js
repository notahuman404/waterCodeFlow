/**
 * Basic JavaScript processor for testing
 */

function main(event) {
    // Process the event
    console.error("Processing event: " + JSON.stringify(event));
    
    // Return a response
    return {
        action: "pass",
        annotations: {
            processed_by: "javascript_processor",
            timestamp: Date.now()
        }
    };
}

module.exports = { main };
