"""
Watcher Python Adapter - High-level API for watching Python variables
"""

import ctypes
import os
import sys
import mmap
import struct
import threading
import weakref
from pathlib import Path
from typing import Any, Optional, Dict, Callable, List, Tuple
from dataclasses import dataclass
import pickle
import json

# ============================================================================
# FFI Bindings to C++ Core
# ============================================================================

class WatcherFFI:
    """FFI interface to the C++ watcher core"""
    
    _lib = None
    _lock = threading.Lock()
    
    @classmethod
    def load_library(cls, lib_path: Optional[str] = None) -> ctypes.CDLL:
        """Load the watcher C++ library"""
        with cls._lock:
            if cls._lib is not None:
                return cls._lib
            
            if lib_path is None:
                # Auto-detect library path
                # From watcher/adapters/python/__init__.py, go up 4 levels to workspace root
                workspace_root = Path(__file__).parent.parent.parent.parent
                lib_dir = workspace_root / "build"
                if not lib_dir.exists():
                    lib_dir = workspace_root / "cmake-build-debug"
                lib_path = lib_dir / "libwatcher_python.so"
            
            cls._lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            cls._lib.watcher_initialize.argtypes = [ctypes.c_char_p]
            cls._lib.watcher_initialize.restype = ctypes.c_char_p
            
            cls._lib.watcher_start.restype = ctypes.c_bool
            cls._lib.watcher_stop.restype = ctypes.c_bool
            
            cls._lib.watcher_register_page.argtypes = [
                ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_uint32
            ]
            cls._lib.watcher_register_page.restype = ctypes.c_char_p
            
            cls._lib.watcher_unregister_page.argtypes = [ctypes.c_char_p]
            cls._lib.watcher_unregister_page.restype = ctypes.c_bool
            
            cls._lib.watcher_read_snapshot.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_size_t)]
            cls._lib.watcher_read_snapshot.restype = ctypes.c_void_p
            
            cls._lib.watcher_write_snapshot.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
            cls._lib.watcher_write_snapshot.restype = ctypes.c_bool
            
            cls._lib.watcher_get_state.restype = ctypes.c_int
            cls._lib.watcher_get_error.restype = ctypes.c_char_p
            
            return cls._lib

# ============================================================================
# Event Flags (from C++ core)
# ============================================================================

FLAG_TRACK_THREADS = 1 << 0
FLAG_TRACK_SQL = 1 << 1
FLAG_TRACK_ALL = 1 << 2
FLAG_TRACK_LOCALS = 1 << 3

PAGE_SIZE = 4096

# ============================================================================
# Shadow Memory Manager
# ============================================================================

class ShadowMemory:
    """Manages mmap'd pages for watched variables"""
    
    def __init__(self, value: Any, serializer: Optional[Callable] = None):
        """
        Allocate and initialize shadow memory for a value
        
        Args:
            value: Python value to watch
            serializer: Optional custom serializer (default: pickle)
        """
        self.serializer = serializer or self._default_serializer
        self.deserializer = self._default_deserializer
        
        # Serialize value
        serialized = self.serializer(value)
        if len(serialized) > PAGE_SIZE - 64:
            raise ValueError(f"Value too large: {len(serialized)} > {PAGE_SIZE - 64}")
        
        # Allocate mmap'd page
        self.mmap_obj = mmap.mmap(-1, PAGE_SIZE, access=mmap.ACCESS_WRITE)
        
        # Store initial page base address (use ctypes to get actual buffer address)
        # Create a ctypes array from the mmap buffer to enable address lookup
        import ctypes
        self.buffer = (ctypes.c_byte * PAGE_SIZE).from_buffer(self.mmap_obj)
        self.page_base = ctypes.addressof(self.buffer)
        
        # Write initial value with length prefix (4 bytes little-endian)
        length_bytes = len(serialized).to_bytes(4, 'little')
        self.mmap_obj[:4] = length_bytes
        self.mmap_obj[4:4+len(serialized)] = serialized
        self.mmap_obj.flush()
        
        # Store data for serialization
        self.data = self.mmap_obj[:]
        
        # Touch page to ensure materialization
        self.mmap_obj[0:1]
    
    def read(self) -> Any:
        """Read current value from shadow memory"""
        # Read length prefix
        length_bytes = self.mmap_obj[:4]
        if length_bytes == b'\x00\x00\x00\x00':
            return None
        length = int.from_bytes(length_bytes, 'little')
        if length == 0 or length > PAGE_SIZE - 4:
            return None
        
        # Read serialized data
        serialized = bytes(self.mmap_obj[4:4+length])
        self.data = serialized
        return self.deserializer(serialized)
    
    def write(self, value: Any):
        """Write value to shadow memory"""
        serialized = self.serializer(value)
        length_bytes = len(serialized).to_bytes(4, 'little')
        self.mmap_obj[:4] = length_bytes
        self.mmap_obj[4:4+len(serialized)] = serialized
        self.mmap_obj.flush()
        self.data = serialized
    
    def get_snapshot(self) -> bytes:
        """Get current memory snapshot"""
        return bytes(self.mmap_obj[:])
    
    def set_snapshot(self, data: bytes):
        """Set memory from snapshot"""
        self.mmap_obj[:len(data)] = data
        self.mmap_obj.flush()
    
    @staticmethod
    def _default_serializer(value: Any) -> bytes:
        """Default serializer using pickle"""
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    
    @staticmethod
    def _default_deserializer(data: bytes) -> Any:
        """Default deserializer using pickle"""
        try:
            return pickle.loads(data)
        except Exception:
            return None
    
    def __del__(self):
        """Cleanup mmap on deletion"""
        if hasattr(self, 'mmap_obj') and self.mmap_obj:
            self.mmap_obj.close()

# ============================================================================
# Proxy Object (Intercepts mutations)
# ============================================================================

class WatchProxy:
    """
    Proxy object that intercepts all mutations and routes them through shadow memory
    
    Usage:
        x = watch(42, name="counter")
        x = x + 1  # Mutation through shadow memory
        x = x * 2  # Another mutation
    """
    
    __slots__ = ('_shadow', '_variable_id', '_name', '_core')
    
    def __init__(self, shadow: ShadowMemory, variable_id: str, name: str):
        object.__setattr__(self, '_shadow', shadow)
        object.__setattr__(self, '_variable_id', variable_id)
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_core', WatcherCore.getInstance())
    
    def __getattr__(self, name: str) -> Any:
        """Get attribute from underlying value"""
        value = object.__getattribute__(self, '_shadow').read()
        return getattr(value, name)
    
    def __setattr__(self, name: str, value: Any):
        """Set attribute on underlying value"""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            shadow = object.__getattribute__(self, '_shadow')
            val = shadow.read()
            setattr(val, name, value)
            shadow.write(val)
    
    def __getitem__(self, key: Any) -> Any:
        """Get item from underlying value"""
        value = object.__getattribute__(self, '_shadow').read()
        return value[key]
    
    def __setitem__(self, key: Any, value: Any):
        """Set item in underlying value"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        val[key] = value
        shadow.write(val)
    
    def __add__(self, other: Any) -> 'WatchProxy':
        """Arithmetic: self + other"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        result = val + other
        shadow.write(result)
        return self
    
    def __sub__(self, other: Any) -> 'WatchProxy':
        """Arithmetic: self - other"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        result = val - other
        shadow.write(result)
        return self
    
    def __mul__(self, other: Any) -> 'WatchProxy':
        """Arithmetic: self * other"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        result = val * other
        shadow.write(result)
        return self
    
    def __truediv__(self, other: Any) -> 'WatchProxy':
        """Arithmetic: self / other"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        result = val / other
        shadow.write(result)
        return self
    
    def __iadd__(self, other: Any) -> 'WatchProxy':
        """In-place: self += other"""
        return self.__add__(other)
    
    def __isub__(self, other: Any) -> 'WatchProxy':
        """In-place: self -= other"""
        return self.__sub__(other)
    
    def __imul__(self, other: Any) -> 'WatchProxy':
        """In-place: self *= other"""
        return self.__mul__(other)
    
    def __itruediv__(self, other: Any) -> 'WatchProxy':
        """In-place: self /= other"""
        return self.__truediv__(other)
    
    def __repr__(self) -> str:
        """String representation"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return f"WatchProxy({val!r})"
    
    def __str__(self) -> str:
        """String conversion"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return str(val)
    
    def __int__(self) -> int:
        """Convert to int"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return int(val)
    
    def __float__(self) -> float:
        """Convert to float"""
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return float(val)
    
    # Comparison operators
    def __eq__(self, other: Any) -> bool:
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return val == other
    
    def __lt__(self, other: Any) -> bool:
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return val < other
    
    def __le__(self, other: Any) -> bool:
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return val <= other
    
    def __gt__(self, other: Any) -> bool:
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return val > other
    
    def __ge__(self, other: Any) -> bool:
        shadow = object.__getattribute__(self, '_shadow')
        val = shadow.read()
        return val >= other

# ============================================================================
# SQL Monkey-Patching
# ============================================================================

class SQLContextManager:
    """Thread-local SQL context tracking"""
    
    _context = threading.local()
    
    @classmethod
    def push_context(cls, query: str, params: tuple = None):
        """Push SQL context"""
        if not hasattr(cls._context, 'stack'):
            cls._context.stack = []
        context = {
            'query': query,
            'params': params,
            'tid': threading.get_ident()
        }
        cls._context.stack.append(context)
        return context
    
    @classmethod
    def pop_context(cls):
        """Pop SQL context"""
        if hasattr(cls._context, 'stack') and cls._context.stack:
            return cls._context.stack.pop()
        return None
    
    @classmethod
    def current_context(cls) -> Optional[Dict]:
        """Get current context"""
        if hasattr(cls._context, 'stack') and cls._context.stack:
            return cls._context.stack[-1]
        return None
    
    @classmethod
    def get_stack(cls):
        """Get the current thread's stack"""
        if not hasattr(cls._context, 'stack'):
            cls._context.stack = []
        return cls._context.stack

def patch_sqlite3(track_sql: bool = False):
    """Monkey-patch sqlite3 for SQL tracking"""
    if not track_sql:
        return
    
    try:
        import sqlite3
        original_execute = sqlite3.Cursor.execute
        
        def patched_execute(self, sql, parameters=None):
            SQLContextManager.push_context(sql, parameters)
            try:
                return original_execute(self, sql, parameters)
            finally:
                SQLContextManager.pop_context()
        
        sqlite3.Cursor.execute = patched_execute
    except ImportError:
        pass

def patch_psycopg2(track_sql: bool = False):
    """Monkey-patch psycopg2 for SQL tracking"""
    if not track_sql:
        return
    
    try:
        import psycopg2.extensions
        original_execute = psycopg2.extensions.cursor.execute
        
        def patched_execute(self, sql, args=None):
            SQLContextManager.push_context(sql, args)
            try:
                return original_execute(self, sql, args)
            finally:
                SQLContextManager.pop_context()
        
        psycopg2.extensions.cursor.execute = patched_execute
    except ImportError:
        pass

# ============================================================================
# Watcher Core (Singleton)
# ============================================================================

class WatcherCore:
    """High-level Python interface to the C++ watcher core"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __init__(self):
        if WatcherCore._initialized:
            return

        self.lib = WatcherFFI.load_library()
        self.variables: Dict[str, Tuple[ShadowMemory, WatchProxy]] = {}
        self.track_sql = False
        self.track_locals = False
        self.track_threads = False
        self.scope_config: Optional[Dict[str, List[Dict[str, str]]]] = None

        WatcherCore._initialized = True
    
    @classmethod
    def getInstance(cls) -> 'WatcherCore':
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def initialize(self, output_dir: str = "./watcher_output",
                  track_threads: bool = False,
                  track_locals: bool = False,
                  track_sql: bool = False,
                  scope_config: Optional[Dict[str, List[Dict[str, str]]]] = None):
        """Initialize the watcher core"""
        self.track_threads = track_threads
        self.track_locals = track_locals
        self.track_sql = track_sql
        self.scope_config = scope_config

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Initialize C++ core
        result = self.lib.watcher_initialize(output_dir.encode())
        if result != b"OK":
            raise RuntimeError(f"Failed to initialize watcher: {result}")

        # Patch SQL libraries if enabled
        if track_sql:
            patch_sqlite3(True)
            patch_psycopg2(True)

        return self.lib.watcher_start()
    
    def watch(self, value: Any, *, name: str = "var",
             track_threads: Optional[bool] = None,
             track_locals: Optional[bool] = None,
             track_sql: Optional[bool] = None,
             mutation_depth: str = "FULL",
             scope: Optional[str] = None,
             file_path: Optional[str] = None) -> WatchProxy:
        """
        Watch a Python variable for mutations

        Usage:
            counter = watch(0, name="counter")
            counter = counter + 1  # Mutation tracked

        Args:
            value: Value to watch
            name: Human-readable name for the variable
            track_threads: Whether to track thread context (default: from core config)
            track_locals: Whether to track local scope (default: from core config)
            track_sql: Whether to track SQL context (default: from core config)
            mutation_depth: "FULL" for full page or byte count
            scope: Variable scope (local/global/both/unknown)
            file_path: File path where variable is defined (used for scope config matching)

        Returns:
            WatchProxy wrapping the value
        """
        # Create shadow memory
        shadow = ShadowMemory(value)

        # Prepare flags
        flags = 0
        if track_threads is None:
            track_threads = self.track_threads
        if track_locals is None:
            track_locals = self.track_locals
        if track_sql is None:
            track_sql = self.track_sql

        if track_threads:
            flags |= FLAG_TRACK_THREADS
        if track_locals:
            flags |= FLAG_TRACK_LOCALS
        if track_sql:
            flags |= FLAG_TRACK_SQL

        # Register with C++ core
        var_id = self.lib.watcher_register_page(
            shadow.page_base,
            PAGE_SIZE,
            name.encode(),
            flags
        ).decode()

        if not var_id or var_id.startswith("Error"):
            raise RuntimeError(f"Failed to register variable: {var_id}")

        # Create proxy
        proxy = WatchProxy(shadow, var_id, name)
        self.variables[var_id] = (shadow, proxy)

        return proxy
    
    def stop(self):
        """Stop the watcher"""
        # Unregister all variables
        for var_id in list(self.variables.keys()):
            self.lib.watcher_unregister_page(var_id.encode())
            del self.variables[var_id]
        
        # Stop core
        return self.lib.watcher_stop()
    
    def get_state(self) -> str:
        """Get core state"""
        state_codes = {
            0: "UNINITIALIZED",
            1: "INITIALIZED",
            2: "RUNNING",
            3: "PAUSED",
            4: "STOPPED",
            5: "ERROR"
        }
        return state_codes.get(self.lib.watcher_get_state(), "UNKNOWN")

# ============================================================================
# Public API
# ============================================================================

# Global watch function injected into user scripts
def watch(value: Any, *, name: str = "var", **kwargs) -> WatchProxy:
    """Watch a variable for mutations"""
    return WatcherCore.getInstance().watch(value, name=name, **kwargs)

__all__ = [
    'watch',
    'WatcherCore',
    'WatchProxy',
    'ShadowMemory',
    'SQLContextManager',
]
