"""
Processor Runner - Executes custom processors

Invokes user-provided processor.main(event) functions with timeout.
Handles both Python and JavaScript processors via subprocess.
"""

import subprocess
import json
import sys
import threading
from typing import Optional, Dict, Any, Callable


class ProcessorAction:
    """Processor response actions"""
    PASS = "pass"        # Don't modify event
    DROP = "drop"        # Skip event (don't write)
    ANNOTATE = "annotate"  # Add annotations
    ENRICH = "enrich"    # Add nested data


class ProcessorResponse:
    """Response from processor"""

    def __init__(self, action: str = ProcessorAction.PASS, **kwargs):
        self.action = action
        self.annotations = kwargs.get('annotations', {})
        self.extra = kwargs.get('extra', {})

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ProcessorResponse':
        """Create response from dictionary"""
        if isinstance(data, dict):
            return ProcessorResponse(
                action=data.get('action', ProcessorAction.PASS),
                annotations=data.get('annotations', {}),
                extra=data.get('extra', {}),
            )
        return ProcessorResponse()


class PythonProcessorRunner:
    """Runs Python processor in subprocess"""

    def __init__(self, processor_path: str, timeout_seconds: float = 0.1):
        """
        Initialize Python processor runner.

        Args:
            processor_path: Path to .py file with main(event) function
            timeout_seconds: Timeout per event (default 100ms)
        """
        self.processor_path = processor_path
        self.timeout_seconds = timeout_seconds

    def invoke(self, event: Dict[str, Any]) -> Optional[ProcessorResponse]:
        """
        Invoke processor on event.

        Args:
            event: Event dictionary from EnrichedEvent.to_dict()

        Returns:
            ProcessorResponse or None if processor fails
        """
        try:
            # Prepare input
            event_json = json.dumps(event)

            # Run processor
            result = subprocess.run(
                [
                    sys.executable, '-c',
                    self._make_processor_wrapper()
                ],
                input=event_json,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            if result.returncode == 0 and result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    return ProcessorResponse.from_dict(response_data)
                except json.JSONDecodeError:
                    # Invalid response JSON
                    return None

            # Processor failed or returned nothing
            return None

        except subprocess.TimeoutExpired:
            # Timeout - skip processor
            return None
        except Exception as e:
            # Any other error
            return None

    def _make_processor_wrapper(self) -> str:
        """Create wrapper script to load and call processor"""
        return f"""
import sys
import json

# Load processor module
spec = __import__('importlib.util').util.spec_from_file_location('proc', '{self.processor_path}')
mod = __import__('importlib.util').util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Read event from stdin
event = json.loads(sys.stdin.read())

# Call processor
response = mod.main(event)

# Output response as JSON
if response is not None:
    if isinstance(response, dict):
        print(json.dumps(response))
    else:
        print(json.dumps({{"action": "pass"}}))
"""


class JavaScriptProcessorRunner:
    """Runs JavaScript processor in subprocess"""

    def __init__(self, processor_path: str, timeout_seconds: float = 0.1):
        """
        Initialize JavaScript processor runner.

        Args:
            processor_path: Path to .js file with main(event) function
            timeout_seconds: Timeout per event (default 100ms)
        """
        self.processor_path = processor_path
        self.timeout_seconds = timeout_seconds

    def invoke(self, event: Dict[str, Any]) -> Optional[ProcessorResponse]:
        """
        Invoke processor on event.

        Args:
            event: Event dictionary

        Returns:
            ProcessorResponse or None if processor fails
        """
        try:
            # Prepare input
            event_json = json.dumps(event)

            # Run processor
            result = subprocess.run(
                ['node', '-e', self._make_processor_wrapper()],
                input=event_json,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )

            if result.returncode == 0 and result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    return ProcessorResponse.from_dict(response_data)
                except json.JSONDecodeError:
                    return None

            return None

        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

    def _make_processor_wrapper(self) -> str:
        """Create wrapper script to load and call processor"""
        return f"""
const fs = require('fs');
const processor = require('{self.processor_path}');

const event = JSON.parse(require('fs').readFileSync(0, 'utf-8'));
const response = processor.main(event);

if (response) {{
    console.log(JSON.stringify(response));
}} else {{
    console.log(JSON.stringify({{"action": "pass"}}));
}}
"""


class ProcessorFactory:
    """Factory for creating processor runners"""

    @staticmethod
    def create_runner(processor_path: str, timeout_seconds: float = 0.1):
        """
        Create appropriate processor runner based on file extension.

        Args:
            processor_path: Path to processor file (.py or .js)
            timeout_seconds: Timeout per event

        Returns:
            Processor runner instance
        """
        if processor_path.endswith('.py'):
            return PythonProcessorRunner(processor_path, timeout_seconds)
        elif processor_path.endswith('.js'):
            return JavaScriptProcessorRunner(processor_path, timeout_seconds)
        else:
            raise ValueError(f"Unsupported processor file: {processor_path}")


class ProcessorChain:
    """Chains multiple processors together"""

    def __init__(self, runners: list):
        """
        Initialize processor chain.

        Args:
            runners: List of processor runners to apply in order
        """
        self.runners = runners

    def invoke(self, event: Dict[str, Any]) -> Optional[ProcessorResponse]:
        """
        Invoke all processors in chain.

        Returns: Final response from last processor, or None if any fails
        """
        response = ProcessorResponse(action=ProcessorAction.PASS)

        for runner in self.runners:
            runner_response = runner.invoke(event)

            if runner_response is None:
                continue

            # Apply response
            if runner_response.action == ProcessorAction.DROP:
                return runner_response  # Stop chain, drop event

            if runner_response.action == ProcessorAction.ANNOTATE:
                event.update({'annotations': runner_response.annotations})

            if runner_response.action == ProcessorAction.ENRICH:
                event.update(runner_response.extra)

            response = runner_response

        return response
