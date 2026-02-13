"""
Watcher CLI - Command-line interface for the Watcher framework
"""

import argparse
import sys
import os
import json
import signal
import importlib.util
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable, Dict, List
from enum import Enum
from dataclasses import dataclass, asdict, field
import logging

from watcher.cli.scope_config_parser import parse_scope_config, is_config_file

# ============================================================================
# Configuration & State Management
# ============================================================================

class CLIState(Enum):
    """CLI state machine"""
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class CLIConfig:
    """CLI configuration"""
    user_script: str
    output_dir: str = "./watcher_output"
    track_threads: bool = False
    track_locals: bool = False
    track_all: bool = False
    track_sql: bool = False
    files_scope: Optional[str] = None
    mutation_depth: str = "FULL"
    custom_processor: Optional[str] = None
    max_queue_size: int = 10000
    log_level: str = "INFO"
    parsed_scope_config: Optional[Dict[str, List[Dict[str, str]]]] = field(default=None, repr=False)

    def to_dict(self):
        return asdict(self)

# ============================================================================
# CLI Orchestrator
# ============================================================================

class WatcherCLI:
    """Main CLI orchestrator"""
    
    # Exit codes (from answer 30)
    EXIT_SUCCESS = 0
    EXIT_VALIDATION_ERROR = 2
    EXIT_RUNTIME_ERROR = 402
    EXIT_CALLBACK_ERROR = 502
    EXIT_PARTIAL_FAILURE = 400
    
    def __init__(self):
        self.state = CLIState.INIT
        self.config: Optional[CLIConfig] = None
        self.user_main: Optional[Callable] = None
        self.processor: Optional[Callable] = None
        self.core: Optional[object] = None
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("watcher")
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _transition_state(self, new_state: CLIState) -> bool:
        """Atomically transition state"""
        valid_transitions = {
            CLIState.INIT: [CLIState.RUNNING, CLIState.ERROR],
            CLIState.RUNNING: [CLIState.PAUSED, CLIState.STOPPED, CLIState.ERROR],
            CLIState.PAUSED: [CLIState.RUNNING, CLIState.STOPPED, CLIState.ERROR],
            CLIState.STOPPED: [CLIState.ERROR],
            CLIState.ERROR: []
        }
        
        if new_state not in valid_transitions.get(self.state, []):
            self.logger.error(f"Invalid state transition: {self.state} -> {new_state}")
            return False
        
        self.state = new_state
        self.logger.info(f"State transition: {new_state.value}")
        return True
    
    def validate_config(self, config: CLIConfig) -> tuple[bool, str]:
        """Validate configuration"""
        # Check user script exists and is Python or JavaScript
        user_script_path = Path(config.user_script)
        if not user_script_path.exists():
            return False, f"User script not found: {config.user_script}"

        if not user_script_path.suffix in ['.py', '.js']:
            return False, f"User script must be .py or .js, got {user_script_path.suffix}"

        # Check output directory is writable
        try:
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create output directory: {e}"

        # Check custom processor if specified
        if config.custom_processor:
            proc_path = Path(config.custom_processor)
            if not proc_path.exists():
                return False, f"Custom processor not found: {config.custom_processor}"
            if not proc_path.suffix in ['.py', '.js']:
                return False, f"Processor must be .py or .js, got {proc_path.suffix}"
            if user_script_path.suffix != proc_path.suffix:
                return False, "Custom processor must be same language as user script"

        # Validate mutation depth
        if config.mutation_depth != "FULL":
            try:
                int(config.mutation_depth)
            except ValueError:
                return False, f"mutation_depth must be 'FULL' or a number, got {config.mutation_depth}"

        # Handle files_scope: check if it's a config file or glob pattern
        if config.files_scope:
            if is_config_file(config.files_scope):
                try:
                    config.parsed_scope_config = parse_scope_config(config.files_scope)
                    self.logger.info(f"Loaded scope configuration from {config.files_scope}")
                except Exception as e:
                    return False, f"Failed to parse scope configuration: {e}"
            # Otherwise treat it as glob pattern (no parsing needed for now)

        return True, "OK"
    
    def load_user_script(self, config: CLIConfig) -> tuple[bool, str]:
        """Load user script and extract main() function"""
        script_path = Path(config.user_script)
        
        if script_path.suffix == '.py':
            return self._load_python_script(str(script_path))
        elif script_path.suffix == '.js':
            return self._load_javascript_script(str(script_path))
        else:
            return False, f"Unsupported script language: {script_path.suffix}"
    
    def _load_python_script(self, script_path: str) -> tuple[bool, str]:
        """Load Python user script"""
        try:
            spec = importlib.util.spec_from_file_location("user_script", script_path)
            if not spec or not spec.loader:
                return False, "Failed to load Python script"

            module = importlib.util.module_from_spec(spec)

            # Inject watch function before loading
            from watcher.adapters.python import watch as original_watch
            from watcher.adapters.python import WatcherCore

            # Create wrapper for watch() that applies scope configuration
            def injected_watch(value, *, name="var", **kwargs):
                """Wrapped watch function that applies scope config"""
                # Get the scope config for this file if available
                core = WatcherCore.getInstance()
                if core.scope_config:
                    # Get the directory-relative path of the script
                    script_rel_path = str(Path(script_path).relative_to(Path.cwd()))

                    # Check if this file is in the scope config
                    for file_pattern, variables in core.scope_config.items():
                        # Simple pattern matching - can be extended to support globs
                        if file_pattern in script_rel_path or script_rel_path in file_pattern:
                            # Look for matching variable name
                            for var_spec in variables:
                                if var_spec['name'] == name:
                                    # Found matching variable - add scope info
                                    kwargs['scope'] = var_spec['scope']
                                    kwargs['file_path'] = script_path
                                    break

                return original_watch(value, name=name, **kwargs)

            module.watch = injected_watch

            sys.modules['user_script'] = module
            spec.loader.exec_module(module)

            # Store main() if it exists, otherwise store a callable that does nothing
            # (since exec_module already executed the module code)
            if hasattr(module, 'main'):
                self.user_main = module.main
            else:
                # Module executed at load time, no main() to call
                self.user_main = lambda: None
            return True, "OK"

        except Exception as e:
            return False, f"Failed to load Python script: {str(e)}"
    
    def _load_javascript_script(self, script_path: str) -> tuple[bool, str]:
        """Load JavaScript user script via Node.js wrapper"""
        try:
            # Validate file exists and is readable
            script_file = Path(script_path)
            if not script_file.exists():
                return False, f"JavaScript script not found: {script_path}"
            
            # Store script path for later execution
            self.user_main = ("javascript", script_path)
            return True, "OK"
        
        except Exception as e:
            return False, f"Failed to load JavaScript script: {str(e)}"
    
    def load_custom_processor(self, config: CLIConfig) -> tuple[bool, str]:
        """Load custom processor script"""
        if not config.custom_processor:
            return True, "OK"  # No processor configured
        
        proc_path = Path(config.custom_processor)
        
        if proc_path.suffix == '.py':
            return self._load_python_processor(str(proc_path))
        elif proc_path.suffix == '.js':
            return self._load_javascript_processor(str(proc_path))
        else:
            return False, f"Unsupported processor language: {proc_path.suffix}"
    
    def _load_python_processor(self, script_path: str) -> tuple[bool, str]:
        """Load Python processor"""
        try:
            spec = importlib.util.spec_from_file_location("processor_module", script_path)
            if not spec or not spec.loader:
                return False, "Failed to load processor"
            
            module = importlib.util.module_from_spec(spec)
            sys.modules['processor_module'] = module
            spec.loader.exec_module(module)
            
            if not hasattr(module, 'main'):
                return False, "Processor must define main(event) function"
            
            self.processor = module.main
            return True, "OK"
        except Exception as e:
            return False, f"Failed to load processor: {str(e)}"
    
    def _load_javascript_processor(self, script_path: str) -> tuple[bool, str]:
        """Load JavaScript processor (validation only, execution via subprocess)"""
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                return False, f"JavaScript processor not found: {script_path}"
            
            # Read script to validate it has main function
            with open(script_path, 'r') as f:
                content = f.read()
            
            if 'main' not in content:
                return False, "Processor must define/export main(event) function"
            
            # Store processor path for later execution via subprocess
            self.processor = ("javascript", script_path)
            return True, "OK"
        except Exception as e:
            return False, f"Failed to load processor: {str(e)}"
    
    def initialize(self, config: CLIConfig) -> bool:
        """Initialize the Watcher system (init phase)"""
        self.logger.info("Initializing Watcher...")
        
        # Validate configuration
        valid, msg = self.validate_config(config)
        if not valid:
            self.logger.error(f"Configuration validation failed: {msg}")
            self._transition_state(CLIState.ERROR)
            return False
        
        self.config = config
        self.logger.setLevel(config.log_level)
        
        # Load user script
        success, msg = self.load_user_script(config)
        if not success:
            self.logger.error(f"Failed to load user script: {msg}")
            self._transition_state(CLIState.ERROR)
            return False
        
        # Load custom processor
        success, msg = self.load_custom_processor(config)
        if not success:
            self.logger.error(f"Failed to load custom processor: {msg}")
            self._transition_state(CLIState.ERROR)
            return False
        
        # Import and initialize Python adapter
        try:
            from watcher.adapters.python import WatcherCore
            self.core = WatcherCore.getInstance()

            # Initialize core with scope config if provided
            init_args = {
                'output_dir': config.output_dir,
                'track_threads': config.track_threads,
                'track_locals': config.track_locals,
                'track_sql': config.track_sql
            }

            if config.parsed_scope_config:
                init_args['scope_config'] = config.parsed_scope_config

            self.core.initialize(**init_args)

            self.logger.info("Watcher core initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize core: {str(e)}")
            self._transition_state(CLIState.ERROR)
            return False
        
        self._transition_state(CLIState.RUNNING)
        return True
    
    def run(self, config: CLIConfig) -> int:
        """Run the Watcher system"""
        self.logger.info("Starting Watcher...")
        
        if not self.initialize(config):
            return self.EXIT_VALIDATION_ERROR
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Execute user main function
            self.logger.info("Executing user script...")
            if self.user_main:
                if isinstance(self.user_main, tuple) and self.user_main[0] == "javascript":
                    # JavaScript script execution via Node.js
                    _, script_path = self.user_main
                    exit_code = self._execute_javascript_script(script_path, config)
                    if exit_code != 0:
                        return exit_code
                else:
                    # Python function execution
                    self.user_main()
            
            self.logger.info("User script completed successfully")
            return self.EXIT_SUCCESS
        
        except Exception as e:
            self.logger.error(f"Error during user script execution: {str(e)}")
            self._transition_state(CLIState.ERROR)
            return self.EXIT_RUNTIME_ERROR
        
        finally:
            self.shutdown()
    
    def _execute_javascript_script(self, script_path: str, config: CLIConfig) -> int:
        """Execute JavaScript user script via Node.js subprocess with watch injection"""
        try:
            import tempfile
            import json
            
            # Create a wrapper that injects watch and executes the user script
            wrapper_code = f"""
const path = require('path');
const module_path = path.resolve('{Path(__file__).parent.parent}/adapters/javascript/index.js');
const {{ watch, WatcherCore }} = require(module_path);

// Inject watch into global scope
global.watch = watch;

// Make watch available as import too
module.exports.watch = watch;

// Load and execute user script
const userScript = require(path.resolve('{script_path}'));

// Call main() if it exists, otherwise script runs at require() time
if (typeof userScript.main === 'function') {{
    userScript.main();
}}
"""
            
            # Write wrapper to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(wrapper_code)
                wrapper_path = f.name
            
            try:
                # Execute wrapper via Node.js
                result = subprocess.run(
                    ['node', wrapper_path],
                    cwd=str(Path.cwd()),
                    capture_output=True,
                    text=True,
                    timeout=None  # No timeout for user scripts
                )
                
                # Print any output
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                
                return result.returncode
            
            finally:
                # Clean up wrapper
                try:
                    os.unlink(wrapper_path)
                except:
                    pass
        
        except subprocess.TimeoutExpired:
            self.logger.error("JavaScript execution timed out")
            return self.EXIT_RUNTIME_ERROR
        except Exception as e:
            self.logger.error(f"Failed to execute JavaScript script: {str(e)}")
            return self.EXIT_RUNTIME_ERROR
    
    def shutdown(self):
        """Graceful shutdown"""
        if self.state == CLIState.STOPPED:
            return  # Already stopped
        
        self.logger.info("Shutting down Watcher...")
        
        try:
            self._transition_state(CLIState.STOPPED)
            
            if self.core:
                self.core.stop()
            
            self.logger.info("Watcher stopped successfully")
        
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            self._transition_state(CLIState.ERROR)

# ============================================================================
# CLI Arguments
# ============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Watcher Framework CLI - Track Python/JavaScript variable mutations",
        epilog="Example: watcher --user-script ./my_app.py --output ./events"
    )
    
    # Required arguments
    parser.add_argument(
        '--user-script',
        required=True,
        help='Path to user script (.py or .js) - optional main() function'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output',
        default='./watcher_output',
        help='Output directory for event logs (default: ./watcher_output)'
    )
    
    parser.add_argument(
        '--track-threads',
        action='store_true',
        help='Track thread context for each mutation (default: disabled)'
    )
    
    parser.add_argument(
        '--track-locals',
        action='store_true',
        help='Track local variables (requires explicit opt-in, default: disabled)'
    )
    
    parser.add_argument(
        '--track-all',
        action='store_true',
        help='Track all variables (memory intensive, default: disabled)'
    )
    
    parser.add_argument(
        '--track-sql',
        action='store_true',
        help='Track SQL query context for mutations (default: disabled)'
    )
    
    parser.add_argument(
        '--files-scope',
        help='Path to scope configuration file or comma-separated glob patterns for file scope (default: all files)'
    )
    
    parser.add_argument(
        '--mutation-depth',
        default='FULL',
        help='Track mutations at FULL page or specify byte limit (default: FULL)'
    )
    
    parser.add_argument(
        '--custom-processor',
        help='Path to custom processor script (.py or .js) with main(event) function'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--max-queue-size',
        type=int,
        default=10000,
        help='Maximum event queue size (default: 10000)'
    )
    
    return parser

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    config = CLIConfig(
        user_script=args.user_script,
        output_dir=args.output,
        track_threads=args.track_threads,
        track_locals=args.track_locals,
        track_all=args.track_all,
        track_sql=args.track_sql,
        files_scope=args.files_scope,
        mutation_depth=args.mutation_depth,
        custom_processor=args.custom_processor,
        log_level=args.log_level,
        max_queue_size=args.max_queue_size
    )
    
    cli = WatcherCLI()
    exit_code = cli.run(config)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
