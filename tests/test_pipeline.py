"""
Unit tests for pipeline.py module.

Tests the core functionality of the data extraction and merge pipeline.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Import pipeline functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from pipeline import (
    get_date_stamp,
    get_log_timestamp,
    parse_output_target,
    build_output_names,
    format_filenum,
    normalise_subfolder,
    build_filepath,
    parse_sig_file,
    is_valid_filenum
)


class TestHelperFunctions:
    """Test helper and formatting functions."""

    def test_get_date_stamp(self):
        """Test that date stamp returns proper format DDMMYYYY."""
        result = get_date_stamp()
        assert len(result) == 8
        assert result.isdigit()

    def test_get_log_timestamp(self):
        """Test that log timestamp returns proper format."""
        result = get_log_timestamp()
        assert ":" in result  # Should contain time separators
        assert len(result) > 8  # Should be longer than just date

    @pytest.mark.parametrize("value,expected", [
        (0, "0000"),
        (1, "0001"),
        (42, "0042"),
        (9999, "9999"),
    ])
    def test_format_filenum(self, value, expected):
        """Test file number formatting with zero-padding."""
        assert format_filenum(value) == expected

    @pytest.mark.parametrize("value", [".", "./", ".\\"])
    def test_normalise_subfolder_current_dir(self, value):
        """Test that current directory references are normalized to empty string."""
        assert normalise_subfolder(value) == ""

    def test_normalise_subfolder_normal_path(self):
        """Test that normal subfolder paths are preserved."""
        assert normalise_subfolder("subfolder") == "subfolder"
        assert normalise_subfolder("nested/folder") == "nested/folder"

    @pytest.mark.parametrize("value,expected", [
        (None, False),
        ("", False),
        ("abc", False),
        ("0", True),
        ("100", True),
        ("9999", True),
        ("10000", False),
    ])
    def test_is_valid_filenum(self, value, expected):
        """Test file number validation."""
        assert is_valid_filenum(value) == expected


class TestBuildFilepath:
    """Test filepath building functionality."""

    def test_build_filepath_simple(self, tmp_path):
        """Test building filepath without subfolder."""
        result = build_filepath(tmp_path, "", "HR", "090923", 0)
        assert result == tmp_path / "HR.090923.0000.sig"

    def test_build_filepath_with_subfolder(self, tmp_path):
        """Test building filepath with subfolder."""
        result = build_filepath(tmp_path, "subfolder", "HR", "090923", 5)
        assert result == tmp_path / "subfolder" / "HR.090923.0005.sig"

    def test_build_filepath_with_different_prefix(self, tmp_path):
        """Test building filepath with non-standard prefix."""
        result = build_filepath(tmp_path, "", "TEST", "090923", 42)
        assert result == tmp_path / "TEST.090923.0042.sig"


class TestParseSigFile:
    """Test .sig file parsing."""

    def test_parse_sig_file_valid(self, sample_sig_file):
        """Test parsing a valid .sig file."""
        wavelengths, reflectance = parse_sig_file(sample_sig_file)
        
        assert wavelengths is not None
        assert reflectance is not None
        assert len(wavelengths) > 0
        assert len(reflectance) > 0
        assert wavelengths[0] == "350.0"
        assert reflectance[0] == "0.15"

    def test_parse_sig_file_nonexistent(self):
        """Test parsing a non-existent file."""
        result = parse_sig_file(Path("/nonexistent/file.sig"))
        assert result == (None, None)

    def test_parse_sig_file_empty(self, temp_dir):
        """Test parsing an empty .sig file."""
        empty_file = temp_dir / "empty.sig"
        empty_file.write_text("")
        
        wavelengths, reflectance = parse_sig_file(empty_file)
        assert wavelengths == []
        assert reflectance == []


class TestParseOutputTarget:
    """Test output target parsing."""

    def test_parse_output_target_none(self, temp_dir):
        """Test with None output value (use default)."""
        result = parse_output_target(None, temp_dir)
        
        assert result["custom_prefix"] is None
        assert result["output_directory"] == temp_dir
        assert result["is_path_output"] is False

    def test_parse_output_target_basename(self, temp_dir):
        """Test with just a base name."""
        result = parse_output_target("myprefix", temp_dir)
        
        assert result["custom_prefix"] == "myprefix"
        assert result["output_directory"] == temp_dir
        assert result["is_path_output"] is False

    def test_parse_output_target_basename_with_csv(self, temp_dir):
        """Test basename with .csv extension."""
        result = parse_output_target("myprefix.csv", temp_dir)
        
        assert result["custom_prefix"] == "myprefix"
        assert result["output_directory"] == temp_dir

    def test_parse_output_target_full_path(self, temp_dir):
        """Test with full path."""
        subdir = temp_dir / "output"
        result = parse_output_target(str(subdir / "myprefix"), temp_dir)
        
        assert result["custom_prefix"] == "myprefix"
        assert result["output_directory"] == subdir
        assert result["is_path_output"] is True

    def test_parse_output_target_empty_raises(self, temp_dir):
        """Test that empty output value raises ValueError."""
        with pytest.raises(ValueError):
            parse_output_target("", temp_dir)


class TestBuildOutputNames:
    """Test output filename generation."""

    def test_build_output_names_default(self):
        """Test output names with no custom prefix."""
        result = build_output_names()
        
        assert "merged_output_name" in result
        assert "heatmap_output_name" in result
        assert "report_output_name" in result
        assert "merged_spectral_data_" in result["merged_output_name"]

    def test_build_output_names_with_prefix(self):
        """Test output names with custom prefix."""
        result = build_output_names(custom_prefix="sydney")
        
        assert "sydney_" in result["merged_output_name"]
        assert "sydney_" in result["heatmap_output_name"]
        assert "sydney_" in result["report_output_name"]
