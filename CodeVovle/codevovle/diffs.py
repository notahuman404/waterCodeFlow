"""
Diff engine for CodeVovle.

Provides:
- Unified diff computation (using difflib)
- Diff validation and analysis
- Patch application (reconstructing text from diffs)
- Empty diff detection

All diff operations use stdlib (difflib) only.
"""

import difflib
from typing import List


class DiffError(Exception):
    """Diff operation error."""
    pass


def compute_unified_diff(old: str, new: str) -> str:
    """
    Compute unified diff between two text strings.
    
    Uses difflib.unified_diff which implements a variant of the Myers algorithm.
    
    Args:
        old: Original text (can be empty string)
        new: New text (can be empty string)
        
    Returns:
        Unified diff format as string (may be empty if texts are identical)
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="a/file",
        tofile="b/file",
        lineterm=""
    ))
    
    return "\n".join(diff_lines) + ("\n" if diff_lines else "")


def is_empty_diff(diff: str) -> bool:
    """
    Check if a diff represents no changes.
    
    A diff is considered empty if:
    - It's an empty string
    - It contains only the three-line header (--- a/file, +++ b/file, and possibly @@ markers)
    
    Args:
        diff: Unified diff text
        
    Returns:
        True if diff has no actual changes, False otherwise
    """
    if not diff or not diff.strip():
        return True
    
    lines = diff.strip().split("\n")
    
    # Count actual change lines (starting with + or -, but not +++ or ---)
    change_lines = 0
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            # These are header lines, not changes
            continue
        if line.startswith("+") or line.startswith("-"):
            # These are actual additions or deletions
            if not line.startswith("+++") and not line.startswith("---"):
                change_lines += 1
    
    return change_lines == 0


def validate_diff_format(diff: str) -> bool:
    """
    Validate that a diff is in valid unified format.
    
    Checks:
    - Contains --- and +++ header lines
    - Each change line starts with +, -, or space
    - No invalid characters
    
    Args:
        diff: Unified diff text
        
    Returns:
        True if diff is valid, False otherwise
    """
    if not diff or not diff.strip():
        # Empty diffs are technically valid (represent no changes)
        return True
    
    lines = diff.strip().split("\n")
    
    if len(lines) < 2:
        return False
    
    # Check for header lines
    has_from_header = any(line.startswith("---") for line in lines)
    has_to_header = any(line.startswith("+++") for line in lines)
    
    if not (has_from_header and has_to_header):
        return False
    
    # Check that change lines are valid
    for line in lines:
        if line.startswith("---") or line.startswith("@@@"):
            # Header lines, these are ok
            continue
        elif line.startswith("+++") or line.startswith("@@"):
            # Header lines, these are ok
            continue
        elif line.startswith("+") or line.startswith("-") or line.startswith(" "):
            # Valid change line
            continue
        else:
            # Invalid line
            return False
    
    return True


def apply_patch(base: str, diff: str) -> str:
    """
    Apply a unified diff patch to a base text.
    
    Reconstructs the new text by applying the diff to the base.
    Uses a simple line-by-line parser for unified diff format.
    
    Args:
        base: Original text (base state)
        diff: Unified diff to apply
        
    Returns:
        Reconstructed text after applying diff
        
    Raises:
        DiffError: If diff cannot be applied to base
    """
    if not diff or is_empty_diff(diff):
        # No changes to apply
        return base
    
    try:
        base_lines = base.splitlines(keepends=True)
        diff_lines = diff.splitlines(keepends=False)
        
        result = []
        base_idx = 0
        diff_idx = 0
        
        while diff_idx < len(diff_lines):
            line = diff_lines[diff_idx]
            
            # Skip header lines
            if line.startswith("---") or line.startswith("+++"):
                diff_idx += 1
                continue
            
            # Process hunk header
            if line.startswith("@@"):
                # Extract the starting line number for the hunk
                # Format: @@ -a,b +c,d @@
                diff_idx += 1
                continue
            
            # Process content lines
            if line.startswith("+"):
                # Addition: add the line (without the + prefix, preserving newline)
                content = line[1:]
                result.append(content if content.endswith("\n") else content + "\n")
                diff_idx += 1
            elif line.startswith("-"):
                # Deletion: skip this line in the base
                if base_idx < len(base_lines):
                    base_idx += 1
                diff_idx += 1
            elif line.startswith(" "):
                # Context line: keep from base (without the space prefix)
                content = line[1:]
                result.append(content if content.endswith("\n") else content + "\n")
                if base_idx < len(base_lines):
                    base_idx += 1
                diff_idx += 1
            else:
                # Unknown line type, skip
                diff_idx += 1
        
        # Join result, but be careful about trailing newlines
        result_str = "".join(result)
        
        # Normalize: ensure consistency with input format
        # If base ended with newline and result is the same, preserve that
        if base.endswith("\n") and not result_str.endswith("\n"):
            result_str += "\n"
        
        return result_str
    except Exception as e:
        raise DiffError(f"Failed to apply patch: {e}") from e


def apply_patch_chain(base: str, diffs: List[str]) -> str:
    """
    Apply a chain of patches sequentially to a base text.
    
    Useful for reconstructing file state from multiple diffs.
    
    Args:
        base: Original text (base state)
        diffs: List of unified diffs to apply in order
        
    Returns:
        Reconstructed text after applying all diffs
        
    Raises:
        DiffError: If any diff cannot be applied
    """
    current = base
    
    for i, diff in enumerate(diffs):
        try:
            current = apply_patch(current, diff)
        except DiffError as e:
            raise DiffError(f"Failed to apply diff {i}: {e}") from e
    
    return current


def get_diff_stats(diff: str) -> dict:
    """
    Get statistics about a diff.
    
    Args:
        diff: Unified diff text
        
    Returns:
        Dictionary with 'additions', 'deletions', 'changes' keys
    """
    additions = 0
    deletions = 0
    
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    
    return {
        "additions": additions,
        "deletions": deletions,
        "changes": additions + deletions
    }
