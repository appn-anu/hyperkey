"""
Unit tests for pipeline.py module.

Tests the core functionality of the data extraction and merge pipeline.
"""

import pytest
from pathlib import Path
import sys
import csv
import json

# Import pipeline functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from pipeline import (
    get_date_stamp,
    get_log_timestamp,
    main,
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


@pytest.mark.integration
def test_main_writes_outputs_to_requested_directory(tmp_path, sample_sig_file):
    """The CLI options control the output directory and filename prefix."""
    sig_file = tmp_path / "HR.090923.0000.sig"
    sig_file.write_bytes(sample_sig_file.read_bytes())
    metadata = tmp_path / "metadata.csv"
    metadata.write_text("FileNum,Date,Prefix,Subfolder\n0,090923,HR,\n", encoding="utf-8")
    output_dir = tmp_path / "output"

    result = main([str(metadata), "-r", str(tmp_path), "-o", str(output_dir), "-n", "sydney"])

    assert result["output_directory"] == output_dir
    assert result["matched_files"] == 1
    assert result["output_csv"].parent == output_dir
    assert result["output_csv"].name.startswith("sydney_merged_spectral_data_")
    with result["output_csv"].open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["350.0"] == "0.15"
    summary = json.loads(result["summary_path"].read_text(encoding="utf-8"))
    assert summary["custom_output_name"] == "sydney"
    assert summary["matched_files"] == 1


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
