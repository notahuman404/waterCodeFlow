#pragma once

#include <watcher_core.hpp>
#include <string>
#include <memory>
#include <vector>
#include <functional>
#include <map>
#include <any>
#include <iostream>

namespace watcher::processor {

// ============================================================================
// Processor Action Types
// ============================================================================

enum class ProcessorAction {
    ANNOTATE,  // Add annotations to event
    DROP,      // Drop event from persistence
    ENRICH,    // Add extra fields
    PASS       // Pass through unchanged
};

struct ProcessorResponse {
    ProcessorAction action;
    std::map<std::string, std::any> annotations;  // For ANNOTATE action
    std::map<std::string, std::any> extra;        // For ENRICH action
};

// ============================================================================
// Custom Processor Interface
// ============================================================================

class CustomProcessor {
public:
    virtual ~CustomProcessor() = default;
    
    /// Process an enriched event
    /// @param event Event to process
    /// @return ProcessorResponse with action and optional data
    virtual ProcessorResponse processEvent(const watcher::EnrichedEvent& event) = 0;
};

// ============================================================================
// Processor Factory & Loader
// ============================================================================

class ProcessorFactory {
public:
    /// Create processor from Python file
    /// @param script_path Path to Python file with processor main() function
    /// @return Pointer to processor, nullptr on error
    static std::unique_ptr<CustomProcessor> createPythonProcessor(const std::string& script_path);
    
    /// Create processor from JavaScript file
    /// @param script_path Path to JavaScript file with processor main() function
    /// @return Pointer to processor, nullptr on error
    static std::unique_ptr<CustomProcessor> createJavaScriptProcessor(const std::string& script_path);
};

// ============================================================================
// Built-in Processors
// ============================================================================

class NoOpProcessor : public CustomProcessor {
public:
    ProcessorResponse processEvent(const watcher::EnrichedEvent& event) override {
        return {ProcessorAction::PASS, {}, {}};
    }
};

class LoggingProcessor : public CustomProcessor {
public:
    explicit LoggingProcessor(std::ostream& out = std::cout) : out_(out) {}
    
    ProcessorResponse processEvent(const watcher::EnrichedEvent& event) override;
    
private:
    std::ostream& out_;
};

class FilteringProcessor : public CustomProcessor {
public:
    using FilterFunc = std::function<bool(const watcher::EnrichedEvent&)>;
    
    explicit FilteringProcessor(FilterFunc filter) : filter_(filter) {}
    
    ProcessorResponse processEvent(const watcher::EnrichedEvent& event) override {
        if (filter_(event)) {
            return {ProcessorAction::PASS, {}, {}};
        } else {
            return {ProcessorAction::DROP, {}, {}};
        }
    }
    
private:
    FilterFunc filter_;
};

}  // namespace watcher::processor
