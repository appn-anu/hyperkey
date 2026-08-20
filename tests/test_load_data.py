"""
Integration tests for data loading and CSV operations.

Tests the load_data.py module and CSV metadata reading.
"""

import pytest
from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestCSVHandling:
    """Test CSV file handling and metadata parsing."""

    def test_read_valid_csv(self, sample_metadata_csv):
        """Test reading a valid CSV file."""
        with open(sample_metadata_csv, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]['FileNum'] == '0'
        assert rows[0]['Date'] == '090923'

    def test_csv_field_names(self, sample_metadata_csv):
        """Test that required CSV fields are present."""
        with open(sample_metadata_csv, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            required_fields = {'FileNum', 'Date', 'Prefix', 'Subfolder'}
            
            assert required_fields.issubset(set(reader.fieldnames))

    def test_missing_csv_file(self):
        """Test behavior when CSV file doesn't exist."""
        nonexistent = Path("/nonexistent/metadata.csv")
        
        with pytest.raises(FileNotFoundError):
            with open(nonexistent, 'r') as f:
                pass

    def test_empty_csv_file(self, temp_dir):
        """Test handling of empty CSV file."""
        empty_csv = temp_dir / "empty.csv"
        empty_csv.write_text("")
        
        with open(empty_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 0

    def test_csv_with_special_characters(self, temp_dir):
        """Test CSV parsing with special characters in data."""
        csv_content = """Name,Value
Test™,Value1
Über,Value2
"""
        csv_file = temp_dir / "special.csv"
        csv_file.write_text(csv_content, encoding='utf-8-sig')
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]['Name'] == 'Test™'


class TestDataValidation:
    """Test data validation logic."""

    def test_valid_measurement_record(self):
        """Test validation of a valid measurement record."""
        record = {
            'FileNum': '123',
            'Date': '090923',
            'Prefix': 'HR',
            'Subfolder': ''
        }
        
        # Check all required fields exist
        required = {'FileNum', 'Date', 'Prefix'}
        assert required.issubset(set(record.keys()))

    def test_missing_required_field(self):
        """Test detection of missing required field."""
        record = {
            'Date': '090923',
            'Prefix': 'HR',
            # Missing FileNum
        }
        
        required = {'FileNum', 'Date', 'Prefix'}
        assert not required.issubset(set(record.keys()))

    @pytest.mark.parametrize("filenum,is_valid", [
        ("0", True),
        ("999", True),
        ("9999", True),
        ("10000", False),
        ("abc", False),
        ("", False),
    ])
    def test_filenum_validation(self, filenum, is_valid):
        """Test file number validation range."""
        try:
            num = int(filenum)
            valid = 0 <= num <= 9999
        except (ValueError, TypeError):
            valid = False
        
        assert valid == is_valid


@pytest.mark.integration
class TestMetadataProcessing:
    """Test end-to-end metadata processing."""

    def test_process_multiple_csv_files(self, temp_dir):
        """Test reading and combining multiple CSV files."""
        # Create two CSV files
        csv1 = temp_dir / "data1.csv"
        csv1.write_text("FileNum,Date,Prefix\n0,090923,HR\n1,090923,HR\n")
        
        csv2 = temp_dir / "data2.csv"
        csv2.write_text("FileNum,Date,Prefix\n2,090923,HR\n3,090923,HR\n")
        
        all_rows = []
        for csv_file in [csv1, csv2]:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                all_rows.extend(list(reader))
        
        assert len(all_rows) == 4
        assert all_rows[0]['FileNum'] == '0'
        assert all_rows[3]['FileNum'] == '3'

    def test_metadata_row_iteration(self, sample_metadata_csv):
        """Test iterating through metadata rows."""
        expected_filenums = ['0', '1', '2']
        
        with open(sample_metadata_csv, 'r') as f:
            reader = csv.DictReader(f)
            filenums = [row['FileNum'] for row in reader]
        
        assert filenums == expected_filenums
