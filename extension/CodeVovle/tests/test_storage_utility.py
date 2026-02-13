"""
Unit tests for storage_utility module.

Tests atomic file I/O operations including:
- Text read/write with atomic semantics
- Directory creation and existence checks
- JSON serialization/deserialization
- Error handling and edge cases
"""

import json
import sys
from pathlib import Path

import pytest

# Import storage_utility from CodeVovle root
import storage_utility as su


class TestReadText:
    """Tests for read_text function."""
    
    def test_read_existing_file(self, sample_file: Path):
        """Test reading an existing file."""
        content = su.read_text(str(sample_file))
        assert content == "initial content\n"
    
    def test_read_empty_file(self, codevovle_root: Path):
        """Test reading an empty file."""
        empty_file = codevovle_root / "empty.txt"
        empty_file.write_text("")
        
        content = su.read_text(str(empty_file))
        assert content == ""
    
    def test_read_large_file(self, codevovle_root: Path):
        """Test reading a large file."""
        large_file = codevovle_root / "large.txt"
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        large_file.write_text(large_content)
        
        content = su.read_text(str(large_file))
        assert len(content) == 10 * 1024 * 1024
        assert content == large_content
    
    def test_read_file_with_unicode(self, codevovle_root: Path):
        """Test reading file with unicode characters."""
        unicode_file = codevovle_root / "unicode.txt"
        unicode_content = "Hello 世界 🌍 Привет\n"
        unicode_file.write_text(unicode_content, encoding='utf-8')
        
        content = su.read_text(str(unicode_file))
        assert content == unicode_content
    
    def test_read_nonexistent_file(self, codevovle_root: Path):
        """Test reading a file that does not exist."""
        nonexistent = codevovle_root / "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError):
            su.read_text(str(nonexistent))
    
    def test_read_file_in_nonexistent_dir(self, codevovle_root: Path):
        """Test reading a file in a directory that does not exist."""
        nonexistent = codevovle_root / "nodir" / "file.txt"
        
        with pytest.raises(FileNotFoundError):
            su.read_text(str(nonexistent))


class TestWriteText:
    """Tests for write_text function."""
    
    def test_write_new_file(self, codevovle_root: Path):
        """Test writing a new file."""
        new_file = codevovle_root / "new.txt"
        
        su.write_text(str(new_file), "new content")
        
        assert new_file.exists()
        assert new_file.read_text(encoding='utf-8') == "new content"
    
    def test_write_overwrites_existing(self, sample_file: Path):
        """Test that write overwrites existing file."""
        su.write_text(str(sample_file), "overwritten")
        
        assert sample_file.read_text(encoding='utf-8') == "overwritten"
    
    def test_write_creates_parent_dirs(self, codevovle_root: Path):
        """Test that write creates parent directories."""
        nested_file = codevovle_root / "a" / "b" / "c" / "file.txt"
        
        su.write_text(str(nested_file), "nested content")
        
        assert nested_file.exists()
        assert nested_file.read_text(encoding='utf-8') == "nested content"
    
    def test_write_empty_string(self, codevovle_root: Path):
        """Test writing an empty string."""
        empty_file = codevovle_root / "empty.txt"
        
        su.write_text(str(empty_file), "")
        
        assert empty_file.exists()
        assert empty_file.read_text(encoding='utf-8') == ""
    
    def test_write_large_file(self, codevovle_root: Path):
        """Test writing a large file."""
        large_file = codevovle_root / "large.txt"
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        
        su.write_text(str(large_file), large_content)
        
        assert large_file.exists()
        assert len(large_file.read_text(encoding='utf-8')) == 10 * 1024 * 1024
    
    def test_write_unicode_content(self, codevovle_root: Path):
        """Test writing unicode content."""
        unicode_file = codevovle_root / "unicode.txt"
        unicode_content = "Hello 世界 🌍 Привет\n"
        
        su.write_text(str(unicode_file), unicode_content)
        
        assert unicode_file.read_text(encoding='utf-8') == unicode_content
    
    def test_write_is_atomic(self, codevovle_root: Path):
        """Test that write is atomic (uses temp + rename)."""
        test_file = codevovle_root / "atomic.txt"
        
        # Write initial content
        su.write_text(str(test_file), "initial")
        
        # Write new content
        su.write_text(str(test_file), "updated")
        
        # File should exist with new content (not corrupted by temp files)
        assert test_file.exists()
        assert test_file.read_text(encoding='utf-8') == "updated"
        
        # No temp files should be left behind
        temp_files = list(codevovle_root.glob(".tmp_*"))
        assert len(temp_files) == 0
    
    def test_write_multiline_content(self, codevovle_root: Path):
        """Test writing multiline content."""
        multiline_file = codevovle_root / "multiline.txt"
        content = "line 1\nline 2\nline 3\n"
        
        su.write_text(str(multiline_file), content)
        
        assert multiline_file.read_text(encoding='utf-8') == content


class TestEnsureDir:
    """Tests for ensure_dir function."""
    
    def test_ensure_existing_dir(self, codevovle_root: Path):
        """Test ensuring a directory that already exists."""
        existing_dir = codevovle_root / "existing"
        existing_dir.mkdir()
        
        # Should not raise
        su.ensure_dir(str(existing_dir))
        
        assert existing_dir.is_dir()
    
    def test_ensure_new_dir(self, codevovle_root: Path):
        """Test creating a new directory."""
        new_dir = codevovle_root / "new"
        
        su.ensure_dir(str(new_dir))
        
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_ensure_nested_dirs(self, codevovle_root: Path):
        """Test creating nested directories."""
        nested_dir = codevovle_root / "a" / "b" / "c"
        
        su.ensure_dir(str(nested_dir))
        
        assert nested_dir.exists()
        assert nested_dir.is_dir()
    
    def test_ensure_dir_idempotent(self, codevovle_root: Path):
        """Test that ensure_dir is idempotent."""
        test_dir = codevovle_root / "idempotent"
        
        su.ensure_dir(str(test_dir))
        su.ensure_dir(str(test_dir))  # Should not raise
        
        assert test_dir.exists()


class TestExists:
    """Tests for exists function."""
    
    def test_exists_file(self, sample_file: Path):
        """Test checking existence of an existing file."""
        assert su.exists(str(sample_file)) is True
    
    def test_exists_dir(self, codevovle_root: Path):
        """Test checking existence of an existing directory."""
        test_dir = codevovle_root / "testdir"
        test_dir.mkdir()
        
        assert su.exists(str(test_dir)) is True
    
    def test_not_exists_file(self, codevovle_root: Path):
        """Test checking a nonexistent file."""
        nonexistent = codevovle_root / "nonexistent.txt"
        
        assert su.exists(str(nonexistent)) is False
    
    def test_not_exists_dir(self, codevovle_root: Path):
        """Test checking a nonexistent directory."""
        nonexistent = codevovle_root / "nonexistentdir"
        
        assert su.exists(str(nonexistent)) is False


class TestReadJson:
    """Tests for read_json function."""
    
    def test_read_valid_json(self, codevovle_root: Path):
        """Test reading a valid JSON file."""
        json_file = codevovle_root / "config.json"
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_file.write_text(json.dumps(data))
        
        result = su.read_json(str(json_file))
        
        assert result == data
    
    def test_read_empty_json_object(self, codevovle_root: Path):
        """Test reading an empty JSON object."""
        json_file = codevovle_root / "empty.json"
        json_file.write_text("{}")
        
        result = su.read_json(str(json_file))
        
        assert result == {}
    
    def test_read_json_with_unicode(self, codevovle_root: Path):
        """Test reading JSON with unicode content."""
        json_file = codevovle_root / "unicode.json"
        data = {"text": "Hello 世界 🌍 Привет"}
        json_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        
        result = su.read_json(str(json_file))
        
        assert result == data
    
    def test_read_nested_json(self, codevovle_root: Path):
        """Test reading nested JSON structures."""
        json_file = codevovle_root / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": {"key": "value"}
                }
            }
        }
        json_file.write_text(json.dumps(data))
        
        result = su.read_json(str(json_file))
        
        assert result == data
    
    def test_read_nonexistent_json(self, codevovle_root: Path):
        """Test reading a nonexistent JSON file."""
        nonexistent = codevovle_root / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            su.read_json(str(nonexistent))
    
    def test_read_invalid_json(self, codevovle_root: Path):
        """Test reading invalid JSON."""
        json_file = codevovle_root / "invalid.json"
        json_file.write_text("{invalid json}")
        
        with pytest.raises(json.JSONDecodeError):
            su.read_json(str(json_file))


class TestWriteJson:
    """Tests for write_json function."""
    
    def test_write_json_dict(self, codevovle_root: Path):
        """Test writing a JSON dictionary."""
        json_file = codevovle_root / "config.json"
        data = {"key": "value", "number": 42}
        
        su.write_json(str(json_file), data)
        
        result = json.loads(json_file.read_text(encoding='utf-8'))
        assert result == data
    
    def test_write_empty_json_dict(self, codevovle_root: Path):
        """Test writing an empty JSON dictionary."""
        json_file = codevovle_root / "empty.json"
        
        su.write_json(str(json_file), {})
        
        result = json.loads(json_file.read_text(encoding='utf-8'))
        assert result == {}
    
    def test_write_complex_json(self, codevovle_root: Path):
        """Test writing complex nested JSON."""
        json_file = codevovle_root / "complex.json"
        data = {
            "strings": ["a", "b", "c"],
            "numbers": [1, 2, 3],
            "nested": {
                "deep": {
                    "value": 42
                }
            },
            "boolean": True,
            "null": None
        }
        
        su.write_json(str(json_file), data)
        
        result = json.loads(json_file.read_text(encoding='utf-8'))
        assert result == data
    
    def test_write_json_with_unicode(self, codevovle_root: Path):
        """Test writing JSON with unicode content."""
        json_file = codevovle_root / "unicode.json"
        data = {"text": "Hello 世界 🌍 Привет"}
        
        su.write_json(str(json_file), data)
        
        result = json.loads(json_file.read_text(encoding='utf-8'))
        assert result == data
    
    def test_write_json_creates_dirs(self, codevovle_root: Path):
        """Test that write_json creates parent directories."""
        json_file = codevovle_root / "a" / "b" / "c" / "config.json"
        data = {"nested": True}
        
        su.write_json(str(json_file), data)
        
        result = json.loads(json_file.read_text(encoding='utf-8'))
        assert result == data


class TestReadJsonSafe:
    """Tests for read_json_safe function."""
    
    def test_read_existing_json(self, codevovle_root: Path):
        """Test reading an existing JSON file."""
        json_file = codevovle_root / "config.json"
        data = {"key": "value"}
        json_file.write_text(json.dumps(data))
        
        result = su.read_json_safe(str(json_file))
        
        assert result == data
    
    def test_read_nonexistent_returns_default(self, codevovle_root: Path):
        """Test that nonexistent file returns default."""
        nonexistent = codevovle_root / "nonexistent.json"
        
        result = su.read_json_safe(str(nonexistent))
        
        assert result == {}
    
    def test_read_nonexistent_custom_default(self, codevovle_root: Path):
        """Test custom default value."""
        nonexistent = codevovle_root / "nonexistent.json"
        custom_default = {"custom": "default"}
        
        result = su.read_json_safe(str(nonexistent), custom_default)
        
        assert result == custom_default
    
    def test_read_invalid_json_returns_default(self, codevovle_root: Path):
        """Test that invalid JSON returns default."""
        json_file = codevovle_root / "invalid.json"
        json_file.write_text("{invalid}")
        
        result = su.read_json_safe(str(json_file))
        
        assert result == {}
    
    def test_read_invalid_json_custom_default(self, codevovle_root: Path):
        """Test custom default for invalid JSON."""
        json_file = codevovle_root / "invalid.json"
        json_file.write_text("{invalid}")
        custom_default = {"error": "default"}
        
        result = su.read_json_safe(str(json_file), custom_default)
        
        assert result == custom_default


class TestStorageUtilityIntegration:
    """Integration tests for storage_utility functions."""
    
    def test_read_write_roundtrip(self, codevovle_root: Path):
        """Test read/write roundtrip."""
        test_file = codevovle_root / "roundtrip.txt"
        original_content = "line 1\nline 2\nline 3\n"
        
        su.write_text(str(test_file), original_content)
        read_content = su.read_text(str(test_file))
        
        assert read_content == original_content
    
    def test_json_read_write_roundtrip(self, codevovle_root: Path):
        """Test JSON read/write roundtrip."""
        test_file = codevovle_root / "roundtrip.json"
        original_data = {
            "string": "value",
            "number": 42,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "unicode": "世界 🌍"
        }
        
        su.write_json(str(test_file), original_data)
        read_data = su.read_json(str(test_file))
        
        assert read_data == original_data
    
    def test_directory_and_file_operations(self, codevovle_root: Path):
        """Test directory creation and file operations."""
        target_dir = codevovle_root / "project" / "src" / "components"
        target_file = target_dir / "component.py"
        
        su.ensure_dir(str(target_dir))
        su.write_text(str(target_file), "def component(): pass")
        
        assert su.exists(str(target_dir))
        assert su.exists(str(target_file))
        assert su.read_text(str(target_file)) == "def component(): pass"
    
    def test_concurrent_file_safety(self, codevovle_root: Path):
        """Test that multiple writes don't interfere."""
        file1 = codevovle_root / "file1.txt"
        file2 = codevovle_root / "file2.txt"
        
        su.write_text(str(file1), "content1")
        su.write_text(str(file2), "content2")
        su.write_text(str(file1), "updated1")
        
        assert su.read_text(str(file1)) == "updated1"
        assert su.read_text(str(file2)) == "content2"
