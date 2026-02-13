"""
Tests for insights engine.

Tests cover:
- Code state reconstruction
- Tick specification parsing
- Diff generation
- Claude API integration (mocked for CI)
- Error handling
"""

import time
from pathlib import Path
from unittest import mock

import pytest

from codevovle.engine import RecordingEngine
from codevovle.insights import InsightsEngine, InsightsError
import storage_utility as su


class TestInsightsReconstruction:
    """Tests for code state reconstruction."""
    
    def test_reconstruct_from_tick(self, codevovle_root: Path, sample_file: Path):
        """Test reconstructing code state."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create versions
        su.write_text(str(sample_file), "version 1\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "version 2\n")
        tick2 = engine.sample()
        
        # Create insights engine
        insights = InsightsEngine(str(sample_file))
        
        # Reconstruct state at tick1
        v1_state = insights._reconstruct_state(str(sample_file), "main", tick1)
        v2_state = insights._reconstruct_state(str(sample_file), "main", tick2)
        
        assert "version 1" in v1_state
        assert "version 2" in v2_state
    
    def test_reconstruct_invalid_tick(self, codevovle_root: Path, sample_file: Path):
        """Test reconstructing invalid tick raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        insights = InsightsEngine(str(sample_file))
        
        with pytest.raises(InsightsError):
            insights._reconstruct_state(str(sample_file), "main", 999)


class TestTickSpecParsing:
    """Tests for tick specification parsing."""
    
    def test_parse_explicit_branch_tick(self, codevovle_root: Path, sample_file: Path):
        """Test parsing explicit branch@tick format."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        insights = InsightsEngine(str(sample_file))
        
        branch, tick = insights._parse_tick_spec("develop@5", str(sample_file))
        
        assert branch == "develop"
        assert tick == 5
    
    def test_parse_implicit_branch_tick(self, codevovle_root: Path, sample_file: Path):
        """Test parsing implicit branch (uses current)."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        insights = InsightsEngine(str(sample_file))
        
        branch, tick = insights._parse_tick_spec("3", str(sample_file))
        
        assert branch == "main"
        assert tick == 3
    
    def test_parse_invalid_spec(self, codevovle_root: Path, sample_file: Path):
        """Test parsing invalid spec raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        insights = InsightsEngine(str(sample_file))
        
        with pytest.raises(InsightsError):
            insights._parse_tick_spec("invalid@abc", str(sample_file))


class TestInsightsGeneration:
    """Tests for insights generation."""
    
    @mock.patch.dict("os.environ", {"CLAUDE_API_KEY": "test-key"})
    @mock.patch("codevovle.insights.InsightsEngine._call_claude")
    def test_generate_insights_mocked(self, mock_claude, codevovle_root: Path, sample_file: Path):
        """Test insights generation with mocked API."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create versions
        su.write_text(str(sample_file), "def hello():\n    pass\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "def hello():\n    print('hello')\n")
        tick2 = engine.sample()
        
        # Mock API response
        mock_claude.return_value = {
            "analysis": "Added print statement to hello function"
        }
        
        insights = InsightsEngine(str(sample_file))
        result = insights.generate_insights("1", "2")
        
        assert result["status"] == "success"
        assert "insights" in result
        assert result["from"] == "main@1"
        assert result["to"] == "main@2"
    
    def test_missing_api_key_error(self, codevovle_root: Path, sample_file: Path, monkeypatch):
        """Test that missing API key raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "v1\n")
        engine.sample()
        
        # Ensure API key is not set
        monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
        
        insights = InsightsEngine(str(sample_file))
        
        with pytest.raises(InsightsError) as exc_info:
            insights.generate_insights("1", "1")
        
        assert "CLAUDE_API_KEY" in str(exc_info.value)
