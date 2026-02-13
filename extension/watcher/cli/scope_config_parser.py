"""
Configuration parser for file-based variable scope specification.

Parses configuration files in the format:
    src/app.py:(local:x,global:counter)
    src/utils.py:(both:helper_func)
    src/config.py:(unknown_property)

Returns structured data for scope-based variable tracking.
"""

import os
from typing import Dict, List, Optional, Tuple


def validate_scope_value(scope: str) -> bool:
    """Validate that scope is one of the allowed values."""
    return scope in {"local", "global", "both", "unknown"}


def extract_variables_from_line(line: str) -> Optional[Tuple[str, List[Dict[str, str]]]]:
    """
    Parse a single configuration line.

    Format: file_path:(scope1:var1,scope2:var2,var3)

    Returns:
        Tuple of (file_path, [{"name": var_name, "scope": scope}, ...])
        or None if parsing fails
    """
    line = line.strip()

    # Skip empty lines and comments
    if not line or line.startswith("#"):
        return None

    # Find the pattern file_path:(
    if ":(" not in line:
        raise ValueError(f"Invalid format (missing :( pattern): {line}")

    # Find the last :( pattern (to handle file paths that might contain colons)
    paren_idx = line.rfind(":(")
    if paren_idx == -1:
        raise ValueError(f"Invalid format (missing :( pattern): {line}")

    file_path = line[:paren_idx].strip()
    var_spec_str = line[paren_idx + 2:].strip()  # Skip the :(

    if not file_path:
        raise ValueError(f"Empty file path in line: {line}")

    # Parse variable specifications from parentheses
    if var_spec_str.endswith(")"):
        var_spec_str = var_spec_str[:-1]
    else:
        raise ValueError(f"Variable specs must end with closing parenthesis: {line}")

    variables = []

    # Split by comma, but handle potential whitespace
    var_entries = [v.strip() for v in var_spec_str.split(",")]

    for entry in var_entries:
        if not entry:
            continue

        # Check if entry has scope prefix (scope:var_name)
        if ":" in entry:
            parts = entry.split(":", 1)
            scope = parts[0].strip()
            var_name = parts[1].strip()

            if not validate_scope_value(scope):
                raise ValueError(f"Invalid scope '{scope}' in: {line}")

            if not var_name:
                raise ValueError(f"Empty variable name in: {line}")

            variables.append({"name": var_name, "scope": scope})
        else:
            # No scope prefix - treat as "unknown" (auto-detect)
            var_name = entry
            if not var_name:
                raise ValueError(f"Empty variable name in: {line}")

            variables.append({"name": var_name, "scope": "unknown"})

    if not variables:
        raise ValueError(f"No variables specified in: {line}")

    return (file_path, variables)


def parse_scope_config(config_file_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse a scope configuration file.

    Args:
        config_file_path: Path to configuration file

    Returns:
        Dict[file_path, [{"name": var_name, "scope": scope}, ...]]

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is malformed
    """
    if not os.path.isfile(config_file_path):
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

    config = {}

    try:
        with open(config_file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                result = extract_variables_from_line(line)
                if result is not None:
                    file_path, variables = result
                    if file_path in config:
                        config[file_path].extend(variables)
                    else:
                        config[file_path] = variables
    except Exception as e:
        raise ValueError(f"Error parsing config file at line {line_num}: {e}")

    if not config:
        raise ValueError("Configuration file is empty or contains no valid entries")

    return config


def is_config_file(path: str) -> bool:
    """
    Check if the given path is a configuration file (exists and is readable).

    Args:
        path: Path to check

    Returns:
        True if path exists as a file, False otherwise
    """
    return os.path.isfile(path)
