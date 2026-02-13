#include "processor.hpp"
#include <iostream>
#include <sstream>
namespace watcher::processor {

// ============================================================================
// Processor Implementations
// ============================================================================

ProcessorResponse LoggingProcessor::processEvent(const watcher::EnrichedEvent& event) {
    out_ << "Event: " << event.event_id << std::endl;
    out_ << "  Symbol: " << event.symbol << std::endl;
    out_ << "  File: " << event.file << ":" << event.line << std::endl;
    out_ << "  TID: " << event.tid << std::endl;
    out_ << "  Deltas: " << event.deltas.size() << std::endl;
    
    return {ProcessorAction::PASS, {}, {}};
}

// ============================================================================
// Processor Factory
// ============================================================================

std::unique_ptr<CustomProcessor> ProcessorFactory::createPythonProcessor(const std::string& script_path) {
    // Placeholder - will be implemented in next phase
    return std::make_unique<NoOpProcessor>();
}

std::unique_ptr<CustomProcessor> ProcessorFactory::createJavaScriptProcessor(const std::string& script_path) {
    // Placeholder - will be implemented in next phase
    return std::make_unique<NoOpProcessor>();
}

}  // namespace watcher::processor
