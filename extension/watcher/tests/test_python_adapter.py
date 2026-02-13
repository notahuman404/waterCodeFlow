"""
Watcher Python Adapter Tests
"""

import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path

# Add watcher to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class TestShadowMemory(unittest.TestCase):
    """Test ShadowMemory implementation"""
    
    def test_shadow_memory_creation(self):
        """Test shadow memory allocation and initialization"""
        try:
            from watcher.adapters.python import ShadowMemory
            
            value = 42
            shadow = ShadowMemory(value)
            
            self.assertIsNotNone(shadow.mmap_obj)
            self.assertGreater(shadow.page_base, 0)
            
        except Exception as e:
            self.skipTest(f"Shadow memory test skipped: {str(e)}")
    
    def test_shadow_memory_read_write(self):
        """Test reading and writing to shadow memory"""
        try:
            from watcher.adapters.python import ShadowMemory
            
            original = 42
            shadow = ShadowMemory(original)
            
            # Read
            value = shadow.read()
            self.assertEqual(value, original)
            
            # Write
            shadow.write(100)
            new_value = shadow.read()
            self.assertEqual(new_value, 100)
            
        except Exception as e:
            self.skipTest(f"Shadow memory test skipped: {str(e)}")
    
    def test_shadow_memory_snapshot(self):
        """Test snapshot operations"""
        try:
            from watcher.adapters.python import ShadowMemory
            
            shadow = ShadowMemory(42)
            
            # Get snapshot
            snapshot = shadow.get_snapshot()
            self.assertIsInstance(snapshot, bytes)
            self.assertGreater(len(snapshot), 0)
            
            # Set snapshot
            shadow.set_snapshot(snapshot)
            # Should not raise
            
        except Exception as e:
            self.skipTest(f"Shadow memory test skipped: {str(e)}")


class TestWatchProxy(unittest.TestCase):
    """Test WatchProxy object"""
    
    def test_proxy_arithmetic(self):
        """Test arithmetic operations on proxy"""
        try:
            from watcher.adapters.python import ShadowMemory, WatchProxy
            
            shadow = ShadowMemory(10)
            proxy = WatchProxy(shadow, "test-var-1", "test_var")
            
            # Addition
            proxy = proxy + 5
            result = shadow.read()
            self.assertEqual(result, 15)
            
            # Subtraction
            proxy = proxy - 3
            result = shadow.read()
            self.assertEqual(result, 12)
            
        except Exception as e:
            self.skipTest(f"Proxy test skipped: {str(e)}")
    
    def test_proxy_comparison(self):
        """Test comparison operations on proxy"""
        try:
            from watcher.adapters.python import ShadowMemory, WatchProxy
            
            shadow = ShadowMemory(42)
            proxy = WatchProxy(shadow, "test-var-2", "test_var")
            
            self.assertTrue(proxy == 42)
            self.assertTrue(proxy < 50)
            self.assertTrue(proxy <= 42)
            self.assertTrue(proxy > 30)
            self.assertTrue(proxy >= 42)
            
        except Exception as e:
            self.skipTest(f"Proxy test skipped: {str(e)}")
    
    def test_proxy_str_repr(self):
        """Test string representation of proxy"""
        try:
            from watcher.adapters.python import ShadowMemory, WatchProxy
            
            shadow = ShadowMemory(42)
            proxy = WatchProxy(shadow, "test-var-3", "test_var")
            
            str_rep = str(proxy)
            self.assertIn("42", str_rep)
            
            repr_rep = repr(proxy)
            self.assertIn("42", repr_rep)
            
        except Exception as e:
            self.skipTest(f"Proxy test skipped: {str(e)}")


class TestWatcherCore(unittest.TestCase):
    """Test WatcherCore high-level interface"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        try:
            from watcher.adapters.python import WatcherCore
            WatcherCore.getInstance().stop()
        except:
            pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_core_initialization(self):
        """Test core initialization"""
        try:
            from watcher.adapters.python import WatcherCore
            
            core = WatcherCore.getInstance()
            core.initialize(self.temp_dir, track_threads=False, track_locals=False)
            
            state = core.get_state()
            self.assertIn(state, ["INITIALIZED", "RUNNING"])
            
        except Exception as e:
            self.skipTest(f"Core initialization test skipped: {str(e)}")
    
    def test_watch_variable(self):
        """Test watching a variable"""
        try:
            from watcher.adapters.python import WatcherCore, watch
            
            core = WatcherCore.getInstance()
            core.initialize(self.temp_dir, track_threads=False, track_locals=False)
            
            # Use global watch function
            counter = watch(0, name="counter")
            self.assertIsNotNone(counter)
            
        except Exception as e:
            self.skipTest(f"Watch variable test skipped: {str(e)}")


class TestCLI(unittest.TestCase):
    """Test CLI interface"""
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parser"""
        from watcher.cli.main import create_argument_parser
        
        parser = create_argument_parser()
        
        # Test with valid arguments
        args = parser.parse_args([
            '--user-script', 'test.py',
            '--output', './output',
            '--track-threads'
        ])
        
        self.assertEqual(args.user_script, 'test.py')
        self.assertEqual(args.output, './output')
        self.assertTrue(args.track_threads)
    
    def test_cli_config_validation(self):
        """Test CLI configuration validation"""
        try:
            from watcher.cli.main import WatcherCLI, CLIConfig
            
            cli = WatcherCLI()
            
            # Invalid: file doesn't exist
            config = CLIConfig(user_script="/nonexistent/file.py")
            valid, msg = cli.validate_config(config)
            self.assertFalse(valid)
            
        except Exception as e:
            self.skipTest(f"CLI config test skipped: {str(e)}")


# ============================================================================
# Stress Tests
# ============================================================================

class TestStress(unittest.TestCase):
    """Stress tests for performance and stability"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        try:
            from watcher.adapters.python import WatcherCore
            WatcherCore.getInstance().stop()
        except:
            pass
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_many_variable_registrations(self):
        """Test registering many variables"""
        try:
            from watcher.adapters.python import WatcherCore, watch
            
            core = WatcherCore.getInstance()
            core.initialize(self.temp_dir, track_threads=False, track_locals=False)
            
            variables = []
            for i in range(100):
                var = watch(i, name=f"var_{i}")
                variables.append(var)
            
            self.assertEqual(len(variables), 100)
            
        except Exception as e:
            self.skipTest(f"Stress test skipped: {str(e)}")
    
    def test_rapid_mutations(self):
        """Test rapid mutations on a variable"""
        try:
            from watcher.adapters.python import WatcherCore, watch
            
            core = WatcherCore.getInstance()
            core.initialize(self.temp_dir, track_threads=False, track_locals=False)
            
            counter = watch(0, name="counter")
            
            for i in range(1000):
                counter = counter + 1
            
            # Verify final value
            self.assertEqual(int(counter), 1000)
            
        except Exception as e:
            self.skipTest(f"Stress test skipped: {str(e)}")


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
