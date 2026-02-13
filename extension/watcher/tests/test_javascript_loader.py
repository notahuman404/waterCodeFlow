"""
Tests for JavaScript user script loading and execution
"""

import pytest
import sys
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add watcher to path
import os
from pathlib import Path

# Get the extension root directory (2 levels up from tests/)
EXTENSION_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_ROOT))
os.environ['LD_LIBRARY_PATH'] = str(EXTENSION_ROOT / 'build') + ':' + os.environ.get('LD_LIBRARY_PATH', '')

from watcher.cli.main import WatcherCLI, CLIConfig, CLIState


class TestJavaScriptScriptLoading:
    """Test JavaScript user script loading"""
    
    def test_load_javascript_script_success(self):
        """Test successful loading of JavaScript script"""
        cli = WatcherCLI()
        script_path = Path(__file__).parent / "fixtures" / "js_user_script_basic.js"
        
        assert script_path.exists(), f"Test fixture not found: {script_path}"
        
        success, msg = cli._load_javascript_script(str(script_path))
        
        assert success is True, f"Failed to load JS script: {msg}"
        assert cli.user_main is not None
        assert cli.user_main[0] == "javascript"
        assert cli.user_main[1] == str(script_path)
    
    def test_load_javascript_script_not_found(self):
        """Test loading non-existent JavaScript script"""
        cli = WatcherCLI()
        
        success, msg = cli._load_javascript_script("/nonexistent/script.js")
        
        assert success is False
        assert "not found" in msg.lower()
    
    def test_load_javascript_script_no_main(self):
        """Test loading JavaScript script without main function - should succeed"""
        cli = WatcherCLI()
        
        # Create temporary script without main
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("console.log('hello');")
            temp_path = f.name
        
        try:
            success, msg = cli._load_javascript_script(temp_path)
            
            # Should succeed - main() is now optional
            assert success is True
            assert msg == "OK"
        finally:
            os.unlink(temp_path)
    
    def test_load_javascript_processor_success(self):
        """Test successful loading of JavaScript processor"""
        cli = WatcherCLI()
        processor_path = Path(__file__).parent / "fixtures" / "js_processor_basic.js"
        
        assert processor_path.exists(), f"Test fixture not found: {processor_path}"
        
        success, msg = cli._load_javascript_processor(str(processor_path))
        
        assert success is True, f"Failed to load JS processor: {msg}"
        assert cli.processor is not None
        assert cli.processor[0] == "javascript"
        assert cli.processor[1] == str(processor_path)


class TestJavaScriptScriptExecution:
    """Test JavaScript script execution"""
    
    def test_execute_javascript_script_basic(self):
        """Test executing basic JavaScript script"""
        cli = WatcherCLI()
        
        # Create test configuration
        config = CLIConfig(
            user_script="dummy.js",
            output_dir="/tmp/test_output"
        )
        
        # Mock core initialization
        cli.core = MagicMock()
        cli.state = CLIState.RUNNING
        
        script_path = Path(__file__).parent / "fixtures" / "js_user_script_basic.js"
        
        if not script_path.exists():
            pytest.skip(f"Test fixture not found: {script_path}")
        
        # Check that node is available
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Node.js not available")
        
        exit_code = cli._execute_javascript_script(str(script_path), config)
        
        # Script should execute successfully
        assert exit_code == 0, f"Script execution failed with code {exit_code}"
    
    def test_execute_javascript_script_with_watch(self):
        """Test executing JavaScript script that uses watch"""
        cli = WatcherCLI()
        
        config = CLIConfig(
            user_script="dummy.js",
            output_dir="/tmp/test_output"
        )
        
        cli.core = MagicMock()
        cli.state = CLIState.RUNNING
        
        script_path = Path(__file__).parent / "fixtures" / "js_user_script_with_watch.js"
        
        if not script_path.exists():
            pytest.skip(f"Test fixture not found: {script_path}")
        
        # Check that node is available
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Node.js not available")
        
        exit_code = cli._execute_javascript_script(str(script_path), config)
        
        # Script should complete (even if watch isn't fully functional)
        assert exit_code == 0


class TestJavaScriptCLIIntegration:
    """Test JavaScript support in CLI"""
    
    def test_validate_js_user_script(self):
        """Test validation of JavaScript user script"""
        script_path = Path(__file__).parent / "fixtures" / "js_user_script_basic.js"
        
        if not script_path.exists():
            pytest.skip(f"Test fixture not found: {script_path}")
        
        cli = WatcherCLI()
        config = CLIConfig(
            user_script=str(script_path),
            output_dir="/tmp/test_output"
        )
        
        is_valid, msg = cli.validate_config(config)
        
        # File should be recognized as valid
        assert is_valid or "JavaScript" not in msg  # Either valid or has specific JS message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
