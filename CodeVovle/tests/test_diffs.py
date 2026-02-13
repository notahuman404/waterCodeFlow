"""
Tests for diff engine.

Tests cover:
- Unified diff computation
- Empty diff detection
- Patch application and reconstruction
- Multi-patch chains
- Edge cases and error handling
"""

import pytest

from codevovle.diffs import (
    compute_unified_diff,
    is_empty_diff,
    apply_patch,
    apply_patch_chain,
    validate_diff_format,
    get_diff_stats,
    DiffError,
)


class TestComputeUnifiedDiff:
    """Tests for compute_unified_diff function."""
    
    def test_identical_texts(self):
        """Test diff of identical texts."""
        text = "line 1\nline 2\nline 3\n"
        
        diff = compute_unified_diff(text, text)
        
        assert is_empty_diff(diff)
    
    def test_single_line_addition(self):
        """Test adding a single line."""
        old = "line 1\nline 2\n"
        new = "line 1\nline 2\nnew line\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "+new line" in diff
        assert not is_empty_diff(diff)
    
    def test_single_line_deletion(self):
        """Test deleting a single line."""
        old = "line 1\nline 2\nline 3\n"
        new = "line 1\nline 3\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "-line 2" in diff
        assert not is_empty_diff(diff)
    
    def test_line_modification(self):
        """Test modifying a line."""
        old = "hello world\n"
        new = "hello python\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "-hello world" in diff
        assert "+hello python" in diff
        assert not is_empty_diff(diff)
    
    def test_multiple_changes(self):
        """Test multiple additions and deletions."""
        old = "a\nb\nc\n"
        new = "a\nx\nc\nd\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "-b" in diff
        assert "+x" in diff
        assert "+d" in diff
        assert not is_empty_diff(diff)
    
    def test_empty_to_content(self):
        """Test creating file from empty."""
        old = ""
        new = "line 1\nline 2\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "+line 1" in diff
        assert "+line 2" in diff
        assert not is_empty_diff(diff)
    
    def test_content_to_empty(self):
        """Test deleting all content."""
        old = "line 1\nline 2\n"
        new = ""
        
        diff = compute_unified_diff(old, new)
        
        assert "-line 1" in diff
        assert "-line 2" in diff
        assert not is_empty_diff(diff)
    
    def test_large_file_diff(self):
        """Test diff of large files."""
        old = "\n".join([f"line {i}" for i in range(1000)])
        new = "\n".join([f"line {i}" if i != 500 else "MODIFIED" for i in range(1000)])
        
        diff = compute_unified_diff(old, new)
        
        assert "-line 500" in diff
        assert "+MODIFIED" in diff
        assert not is_empty_diff(diff)
    
    def test_unicode_content(self):
        """Test diff with unicode."""
        old = "Hello world\n"
        new = "Hello 世界\n"
        
        diff = compute_unified_diff(old, new)
        
        assert "-Hello world" in diff
        assert "+Hello 世界" in diff


class TestIsEmptyDiff:
    """Tests for is_empty_diff function."""
    
    def test_empty_string(self):
        """Test that empty string is empty diff."""
        assert is_empty_diff("") is True
    
    def test_whitespace_only(self):
        """Test that whitespace-only string is empty diff."""
        assert is_empty_diff("   \n  \n") is True
    
    def test_header_only(self):
        """Test that header-only diff is empty diff."""
        diff = "--- a/file\n+++ b/file\n"
        assert is_empty_diff(diff) is True
    
    def test_with_hunk_header(self):
        """Test header with hunk marker but no changes."""
        diff = "--- a/file\n+++ b/file\n@@ -1,3 +1,3 @@\n"
        assert is_empty_diff(diff) is True
    
    def test_with_addition(self):
        """Test diff with additions is not empty."""
        diff = "--- a/file\n+++ b/file\n+new line\n"
        assert is_empty_diff(diff) is False
    
    def test_with_deletion(self):
        """Test diff with deletions is not empty."""
        diff = "--- a/file\n+++ b/file\n-old line\n"
        assert is_empty_diff(diff) is False
    
    def test_with_context_and_change(self):
        """Test diff with context and changes is not empty."""
        diff = "--- a/file\n+++ b/file\n context\n+added\n"
        assert is_empty_diff(diff) is False


class TestValidateDiffFormat:
    """Tests for validate_diff_format function."""
    
    def test_valid_diff(self):
        """Test valid unified diff."""
        diff = "--- a/file\n+++ b/file\n+new line\n"
        assert validate_diff_format(diff) is True
    
    def test_empty_diff(self):
        """Test that empty diff is valid."""
        assert validate_diff_format("") is True
    
    def test_missing_from_header(self):
        """Test diff missing --- header."""
        diff = "+++ b/file\n+new line\n"
        assert validate_diff_format(diff) is False
    
    def test_missing_to_header(self):
        """Test diff missing +++ header."""
        diff = "--- a/file\n+new line\n"
        assert validate_diff_format(diff) is False
    
    def test_with_hunk_marker(self):
        """Test diff with hunk marker is valid."""
        diff = "--- a/file\n+++ b/file\n@@ -1,3 +1,4 @@\n+new\n"
        assert validate_diff_format(diff) is True
    
    def test_context_lines(self):
        """Test that context lines are valid."""
        diff = "--- a/file\n+++ b/file\n context\n-old\n+new\n"
        assert validate_diff_format(diff) is True


class TestApplyPatch:
    """Tests for apply_patch function."""
    
    def test_apply_empty_patch(self):
        """Test applying empty patch returns original."""
        base = "line 1\nline 2\n"
        diff = ""
        
        result = apply_patch(base, diff)
        
        assert result == base
    
    def test_apply_simple_addition(self):
        """Test applying simple addition."""
        base = "line 1\n"
        old = "line 1\n"
        new = "line 1\nnew line\n"
        diff = compute_unified_diff(old, new)
        
        result = apply_patch(base, diff)
        
        assert "new line" in result
    
    def test_apply_simple_deletion(self):
        """Test applying simple deletion."""
        base = "line 1\nline 2\n"
        old = "line 1\nline 2\n"
        new = "line 1\n"
        diff = compute_unified_diff(old, new)
        
        result = apply_patch(base, diff)
        
        assert result == new
    
    def test_apply_modification(self):
        """Test applying line modification."""
        base = "hello\n"
        old = "hello\n"
        new = "world\n"
        diff = compute_unified_diff(old, new)
        
        result = apply_patch(base, diff)
        
        assert result == new
    
    def test_roundtrip_complex_changes(self):
        """Test complete roundtrip: original -> diff -> reconstruction."""
        old = "a\nb\nc\nd\ne\n"
        new = "a\nx\nc\ny\ne\nf\n"
        
        diff = compute_unified_diff(old, new)
        result = apply_patch(old, diff)
        
        assert result == new
    
    def test_apply_patch_empty_to_content(self):
        """Test applying patch from empty file."""
        base = ""
        old = ""
        new = "line 1\nline 2\n"
        diff = compute_unified_diff(old, new)
        
        result = apply_patch(base, diff)
        
        assert result == new


class TestApplyPatchChain:
    """Tests for apply_patch_chain function."""
    
    def test_single_patch(self):
        """Test applying single patch via chain."""
        base = "line 1\n"
        diff1 = compute_unified_diff("line 1\n", "line 1\nnew\n")
        
        result = apply_patch_chain(base, [diff1])
        
        assert "new" in result
    
    def test_two_patches(self):
        """Test applying two sequential patches."""
        base = "a\n"
        
        # First patch: a -> a, b
        diff1 = compute_unified_diff("a\n", "a\nb\n")
        
        # Apply first patch to base
        intermediate = apply_patch(base, diff1)
        
        # Second patch: a, b -> a, b, c
        diff2 = compute_unified_diff("a\nb\n", "a\nb\nc\n")
        
        # Apply both via chain
        result = apply_patch_chain(base, [diff1, diff2])
        
        assert result == "a\nb\nc\n"
    
    def test_three_patches_chain(self):
        """Test applying chain of three patches."""
        base = "1\n"
        
        # 1 -> 1, 2
        diff1 = compute_unified_diff("1\n", "1\n2\n")
        
        # 1, 2 -> 1, 2, 3
        diff2 = compute_unified_diff("1\n2\n", "1\n2\n3\n")
        
        # 1, 2, 3 -> 1, 2, 3, 4
        diff3 = compute_unified_diff("1\n2\n3\n", "1\n2\n3\n4\n")
        
        result = apply_patch_chain(base, [diff1, diff2, diff3])
        
        assert result == "1\n2\n3\n4\n"
    
    def test_empty_diffs_in_chain(self):
        """Test chain with empty diffs (no changes)."""
        base = "a\n"
        
        diff1 = compute_unified_diff("a\n", "a\nb\n")
        diff2 = compute_unified_diff("a\nb\n", "a\nb\n")  # No change
        
        result = apply_patch_chain(base, [diff1, diff2])
        
        assert result == "a\nb\n"


class TestGetDiffStats:
    """Tests for get_diff_stats function."""
    
    def test_stats_additions_only(self):
        """Test stats for additions."""
        diff = compute_unified_diff("a\n", "a\nb\nc\n")
        stats = get_diff_stats(diff)
        
        assert stats["additions"] == 2
        assert stats["deletions"] == 0
        assert stats["changes"] == 2
    
    def test_stats_deletions_only(self):
        """Test stats for deletions."""
        diff = compute_unified_diff("a\nb\nc\n", "a\n")
        stats = get_diff_stats(diff)
        
        assert stats["deletions"] == 2
        assert stats["additions"] == 0
        assert stats["changes"] == 2
    
    def test_stats_mixed(self):
        """Test stats for mixed changes."""
        diff = compute_unified_diff("a\nb\nc\n", "a\nx\nc\nd\n")
        stats = get_diff_stats(diff)
        
        assert stats["additions"] >= 1  # At least x and d
        assert stats["deletions"] >= 1  # At least b
        assert stats["changes"] > 0


class TestDiffIntegration:
    """Integration tests for diff engine."""
    
    def test_empty_to_complex(self):
        """Test progression from empty to complex file."""
        states = [
            "",
            "def hello():\n",
            "def hello():\n    pass\n",
            "def hello():\n    pass\n\ndef world():\n    pass\n"
        ]
        
        diffs = []
        for i in range(len(states) - 1):
            diff = compute_unified_diff(states[i], states[i + 1])
            diffs.append(diff)
        
        # Reconstruct from empty + all diffs
        reconstructed = apply_patch_chain("", diffs)
        
        assert reconstructed == states[-1]
    
    def test_complex_file_history(self):
        """Test complex file with multiple changes."""
        v1 = "class Foo:\n    def method(self):\n        return 1\n"
        v2 = "class Foo:\n    def method(self):\n        return 2\n    def other(self):\n        pass\n"
        v3 = "class Bar:\n    def method(self):\n        return 2\n    def other(self):\n        pass"
        
        diff1 = compute_unified_diff(v1, v2)
        diff2 = compute_unified_diff(v2, v3)
        
        result = apply_patch_chain(v1, [diff1, diff2])
        
        # Normalize: remove trailing whitespace variations
        assert result.strip() == v3.strip()
    
    def test_unicode_progression(self):
        """Test file with unicode characters."""
        states = [
            "Hello\n",
            "Hello 世界\n",
            "你好 Welcome\n"
        ]
        
        diff1 = compute_unified_diff(states[0], states[1])
        diff2 = compute_unified_diff(states[1], states[2])
        
        result = apply_patch_chain(states[0], [diff1, diff2])
        
        assert result == states[2]
        assert "世界" in result or "你好" in result
