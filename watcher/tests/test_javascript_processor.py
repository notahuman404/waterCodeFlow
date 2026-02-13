"""
Tests for JavaScript processor execution
"""

import pytest
import sys
import os
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, '/workspaces/WaterCodeFlow')
os.environ['LD_LIBRARY_PATH'] = '/workspaces/WaterCodeFlow/build:' + os.environ.get('LD_LIBRARY_PATH', '')

from watcher.cli.processor_runner import JavaScriptProcessorRunner, ProcessorFactory


class TestJavaScriptProcessor:
    """Test JavaScript processor execution"""
    
    def test_create_javascript_processor_runner(self):
        """Test creating a JavaScript processor runner"""
        processor_path = Path(__file__).parent / "fixtures" / "js_processor_basic.js"
        
        if not processor_path.exists():
            pytest.skip(f"Test fixture not found: {processor_path}")
        
        runner = ProcessorFactory.create_runner(str(processor_path))
        
        assert isinstance(runner, JavaScriptProcessorRunner)
    
    def test_invoke_javascript_processor(self):
        """Test invoking a JavaScript processor"""
        processor_path = Path(__file__).parent / "fixtures" / "js_processor_basic.js"
        
        if not processor_path.exists():
            pytest.skip(f"Test fixture not found: {processor_path}")
        
        # Check that node is available
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Node.js not available")
        
        runner = JavaScriptProcessorRunner(str(processor_path), timeout_seconds=5.0)
        
        # Create test event
        event = {
            'event_id': 'test_1',
            'timestamp_ns': 1000000,
            'variable_name': 'test_var',
            'deltas': []
        }
        
        response = runner.invoke(event)
        
        # Response should not be None
        assert response is not None
        assert response.action == "pass"
    
    def test_javascript_processor_with_annotations(self):
        """Test JavaScript processor that adds annotations"""
        processor_path = Path(__file__).parent / "fixtures" / "js_processor_basic.js"
        
        if not processor_path.exists():
            pytest.skip(f"Test fixture not found: {processor_path}")
        
        # Check that node is available
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Node.js not available")
        
        runner = JavaScriptProcessorRunner(str(processor_path), timeout_seconds=5.0)
        
        event = {
            'event_id': 'test_2',
            'timestamp_ns': 2000000,
            'variable_name': 'test_var2',
        }
        
        response = runner.invoke(event)
        
        # Check that annotations were added
        assert response is not None
        assert hasattr(response, 'annotations')


class TestJavaScriptProcessorIntegration:
    """Integration tests for JavaScript processors with events"""
    
    def test_processor_factory_creates_js_runner(self):
        """Test that ProcessorFactory correctly creates JS runners"""
        processor_path = Path(__file__).parent / "fixtures" / "js_processor_basic.js"
        
        if not processor_path.exists():
            pytest.skip(f"Test fixture not found: {processor_path}")
        
        runner = ProcessorFactory.create_runner(str(processor_path))
        
        assert runner is not None
        assert isinstance(runner, JavaScriptProcessorRunner)
        assert runner.processor_path == str(processor_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
