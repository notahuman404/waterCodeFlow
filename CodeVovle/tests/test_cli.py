"""
Tests for CLI argument parsing and CWD validation.

Tests cover:
- CWD validation (must be 'CodeVovle')
- File path validation (must be inside CodeVovle)
- All argument parsing scenarios
"""

import os
import sys
from pathlib import Path

import pytest

from codevovle.cli import (
    validate_cwd,
    validate_file_path,
    parse_args,
    create_argument_parser,
    CLIError,
)


class TestValidateCwd:
    """Tests for CWD validation."""
    
    def test_validate_cwd_success(self, codevovle_root: Path):
        """Test that validation passes when in CodeVovle directory."""
        # codevovle_root fixture already changes to CodeVovle directory
        assert os.getcwd().endswith("CodeVovle")
        
        # Should not raise
        validate_cwd()
    
    def test_validate_cwd_failure(self, codevovle_root: Path):
        """Test that validation fails when not in CodeVovle directory."""
        original_cwd = os.getcwd()
        
        try:
            # Change to parent directory
            os.chdir(codevovle_root.parent)
            
            with pytest.raises(CLIError) as exc_info:
                validate_cwd()
            
            assert "must be run from a directory named 'CodeVovle'" in str(exc_info.value)
        finally:
            os.chdir(original_cwd)
    
    def test_validate_cwd_wrong_name(self, tmp_path: Path):
        """Test that validation fails with wrong directory name."""
        wrong_dir = tmp_path / "WrongName"
        wrong_dir.mkdir()
        
        original_cwd = os.getcwd()
        try:
            os.chdir(str(wrong_dir))
            
            with pytest.raises(CLIError):
                validate_cwd()
        finally:
            os.chdir(original_cwd)


class TestValidateFilePath:
    """Tests for file path validation."""
    
    def test_validate_file_inside_codevovle(self, codevovle_root: Path):
        """Test that validation passes for files inside CodeVovle."""
        file_path = "src/main.py"
        
        result = validate_file_path(file_path)
        
        assert result.is_absolute()
        assert str(codevovle_root) in str(result)
    
    def test_validate_nested_file(self, codevovle_root: Path):
        """Test validation for nested file paths."""
        file_path = "a/b/c/file.py"
        
        result = validate_file_path(file_path)
        
        assert result.is_absolute()
        assert str(codevovle_root) in str(result)
    
    def test_validate_file_outside_codevovle(self, codevovle_root: Path):
        """Test that validation fails for files outside CodeVovle."""
        outside_path = "../outside.py"
        
        with pytest.raises(CLIError) as exc_info:
            validate_file_path(outside_path)
        
        assert "must be inside the CodeVovle directory" in str(exc_info.value)
    
    def test_validate_absolute_path_outside(self, codevovle_root: Path, tmp_path: Path):
        """Test validation with absolute path outside CodeVovle."""
        outside_file = tmp_path / "outside.py"
        
        with pytest.raises(CLIError):
            validate_file_path(str(outside_file))
    
    def test_validate_file_at_root(self, codevovle_root: Path):
        """Test validation for file at CodeVovle root."""
        file_path = "main.py"
        
        result = validate_file_path(file_path)
        
        assert result.is_absolute()


class TestArgumentsParsing:
    """Tests for argument parsing."""
    
    def test_parse_record_command(self):
        """Test parsing record command."""
        args = parse_args(["record", "--file", "main.py", "--interval", "5"])
        
        assert args.command == "record"
        assert args.file == "main.py"
        assert args.interval == 5.0
        assert args.out is None
    
    def test_parse_record_with_out(self):
        """Test parsing record command with output directory."""
        args = parse_args(["record", "--file", "main.py", "--interval", "10", "--out", "/tmp"])
        
        assert args.command == "record"
        assert args.file == "main.py"
        assert args.interval == 10.0
        assert args.out == "/tmp"
    
    def test_parse_revert_command(self):
        """Test parsing revert command."""
        args = parse_args(["revert", "--file", "main.py", "--at", "5"])
        
        assert args.command == "revert"
        assert args.file == "main.py"
        assert args.at == "5"
    
    def test_parse_branch_list(self):
        """Test parsing branch list command."""
        args = parse_args(["branch", "list", "--file", "main.py"])
        
        assert args.command == "branch"
        assert args.branch_command == "list"
        assert args.file == "main.py"
    
    def test_parse_branch_rename(self):
        """Test parsing branch rename command."""
        args = parse_args(["branch", "rename", "--file", "main.py", "old_name", "new_name"])
        
        assert args.command == "branch"
        assert args.branch_command == "rename"
        assert args.file == "main.py"
        assert args.branch == "old_name"
        assert args.new_name == "new_name"
    
    def test_parse_branch_jump(self):
        """Test parsing branch jump command."""
        args = parse_args(["branch", "jump", "--file", "main.py", "develop"])
        
        assert args.command == "branch"
        assert args.branch_command == "jump"
        assert args.file == "main.py"
        assert args.branch == "develop"
    
    def test_parse_insights_command(self):
        """Test parsing insights command."""
        args = parse_args(["insights", "--file", "main.py", "--from", "1", "--to", "5"])
        
        assert args.command == "insights"
        assert args.file == "main.py"
        assert args.from_spec == "1"
        assert args.to_spec == "5"
    
    def test_parse_insights_with_branch(self):
        """Test parsing insights with branch notation."""
        args = parse_args(["insights", "--file", "main.py", "--from", "main@1", "--to", "develop@5"])
        
        assert args.command == "insights"
        assert args.from_spec == "main@1"
        assert args.to_spec == "develop@5"
    
    def test_parse_status_command(self):
        """Test parsing status command."""
        args = parse_args(["status", "--file", "main.py"])
        
        assert args.command == "status"
        assert args.file == "main.py"


class TestArgumentsValidation:
    """Tests for argument validation and error cases."""
    
    def test_missing_file_argument(self):
        """Test that missing --file is caught."""
        with pytest.raises(CLIError):
            parse_args(["record", "--interval", "5"])
    
    def test_missing_interval_in_record(self):
        """Test that missing --interval in record is caught."""
        with pytest.raises(CLIError):
            parse_args(["record", "--file", "main.py"])
    
    def test_missing_at_in_revert(self):
        """Test that missing --at in revert is caught."""
        with pytest.raises(CLIError):
            parse_args(["revert", "--file", "main.py"])
    
    def test_no_command(self):
        """Test that missing command raises error."""
        with pytest.raises(CLIError):
            parse_args([])
    
    def test_invalid_command(self):
        """Test that invalid command raises error."""
        with pytest.raises(CLIError):
            parse_args(["invalid_command", "--file", "main.py"])
    
    def test_branch_without_subcommand(self):
        """Test that branch without subcommand raises error."""
        with pytest.raises(CLIError):
            parse_args(["branch", "--file", "main.py"])
    
    def test_float_interval(self):
        """Test that interval accepts float values."""
        args = parse_args(["record", "--file", "main.py", "--interval", "2.5"])
        
        assert args.interval == 2.5
    
    def test_negative_interval(self):
        """Test that negative interval is parsed (validation elsewhere)."""
        args = parse_args(["record", "--file", "main.py", "--interval", "-5"])
        
        assert args.interval == -5


class TestArgumentParserCreation:
    """Tests for argument parser setup."""
    
    def test_parser_has_subparsers(self):
        """Test that parser has all expected subparsers."""
        parser = create_argument_parser()
        
        # Check that parser can parse each command
        for cmd in ["record", "revert", "branch", "insights", "status"]:
            args_list = [cmd, "--file", "test.py"]
            if cmd == "record":
                args_list.append("--interval")
                args_list.append("5")
            elif cmd == "revert":
                args_list.append("--at")
                args_list.append("1")
            elif cmd == "branch":
                args_list[1:1] = ["list"]
            elif cmd == "insights":
                args_list.extend(["--from", "1", "--to", "5"])
            
            result = parser.parse_args(args_list)
            assert result.command == cmd
    
    def test_parser_prog_name(self):
        """Test that parser has correct program name."""
        parser = create_argument_parser()
        assert parser.prog == "codevovle"


class TestCLIIntegration:
    """Integration tests for CLI argument parsing."""
    
    def test_record_command_full_flow(self, codevovle_root: Path):
        """Test complete record command parsing and validation."""
        args = parse_args(["record", "--file", "src/main.py", "--interval", "5"])
        
        # Validate file path
        file_path = validate_file_path(args.file)
        
        assert args.command == "record"
        assert file_path.is_absolute()
        assert "src" in str(file_path)
    
    def test_revert_command_full_flow(self, codevovle_root: Path):
        """Test complete revert command parsing and validation."""
        args = parse_args(["revert", "--file", "src/main.py", "--at", "3"])
        
        file_path = validate_file_path(args.file)
        
        assert args.command == "revert"
        assert args.at == "3"
        assert file_path.is_absolute()
    
    def test_branch_jump_full_flow(self, codevovle_root: Path):
        """Test complete branch jump command parsing and validation."""
        args = parse_args(["branch", "jump", "--file", "main.py", "develop"])
        
        file_path = validate_file_path(args.file)
        
        assert args.command == "branch"
        assert args.branch_command == "jump"
        assert args.branch == "develop"
        assert file_path.is_absolute()
    
    def test_insights_command_full_flow(self, codevovle_root: Path):
        """Test complete insights command parsing and validation."""
        args = parse_args(["insights", "--file", "main.py", "--from", "branch@1", "--to", "branch@5"])
        
        file_path = validate_file_path(args.file)
        
        assert args.command == "insights"
        assert args.from_spec == "branch@1"
        assert args.to_spec == "branch@5"
        assert file_path.is_absolute()
