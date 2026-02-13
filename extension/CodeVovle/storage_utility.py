"""
Atomic file I/O utilities for CodeVovle.

Provides safe read/write operations with atomic semantics using tempfile + rename pattern.
All operations are cross-platform safe and use stdlib only (no external dependencies).
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict


def read_text(path: str) -> str:
    """
    Read entire text file atomically.
    
    Args:
        path: File path to read
        
    Returns:
        File contents as string
        
    Raises:
        FileNotFoundError: If file does not exist
        IOError: If read fails
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    try:
        return p.read_text(encoding='utf-8')
    except Exception as e:
        raise IOError(f"Failed to read file {path}: {e}") from e


def write_text(path: str, data: str) -> None:
    """
    Write text file atomically using tempfile + rename pattern.
    
    Creates a temporary file in the same directory as the target, writes data,
    then atomically renames it to the final location. This ensures:
    - Partial writes are never visible (all-or-nothing)
    - No data corruption if process is interrupted
    
    Args:
        path: File path to write
        data: Text content to write
        
    Raises:
        IOError: If write fails
    """
    p = Path(path)
    
    try:
        # Ensure parent directory exists
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file in same directory (ensures same filesystem)
        fd, temp_path = tempfile.mkstemp(
            dir=str(p.parent),
            prefix='.tmp_',
            suffix='.tmp'
        )
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(data)
            
            # Atomic rename (rename is atomic on POSIX and Windows)
            os.replace(temp_path, str(p))
        except Exception:
            # Clean up temp file if something went wrong
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise
    except Exception as e:
        raise IOError(f"Failed to write file {path}: {e}") from e


def ensure_dir(path: str) -> None:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path to create
        
    Raises:
        OSError: If directory creation fails
    """
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise OSError(f"Failed to create directory {path}: {e}") from e


def exists(path: str) -> bool:
    """
    Check if file or directory exists.
    
    Args:
        path: File or directory path to check
        
    Returns:
        True if path exists, False otherwise
    """
    return Path(path).exists()


def read_json(path: str) -> Dict[str, Any]:
    """
    Read JSON file atomically.
    
    Args:
        path: JSON file path
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If JSON is invalid
        IOError: If read fails
    """
    try:
        text = read_text(path)
        return json.loads(text)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {path}: {e.msg}",
            e.doc,
            e.pos
        ) from e
    except IOError:
        raise


def write_json(path: str, data: Dict[str, Any]) -> None:
    """
    Write JSON file atomically using write_text.
    
    Args:
        path: JSON file path
        data: Dictionary to serialize
        
    Raises:
        IOError: If write fails
    """
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        write_text(path, json_str)
    except (TypeError, ValueError) as e:
        raise IOError(f"Failed to serialize JSON for {path}: {e}") from e
    except IOError:
        raise


def read_json_safe(path: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Read JSON file, returning default if file does not exist or is invalid.
    
    Args:
        path: JSON file path
        default: Value to return if file missing or invalid (default: {})
        
    Returns:
        Parsed JSON or default
    """
    if default is None:
        default = {}
    
    try:
        return read_json(path)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return default
