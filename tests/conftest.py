"""
Pytest configuration and shared fixtures for HyperKey tests.
"""

import sys
from pathlib import Path
import tempfile
import shutil

import pytest

# Add scripts directory to path so we can import modules
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup after test
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_sig_file(temp_dir):
    """Create a sample .sig file for testing."""
    sig_content = """Header Information
Date: 2023-09-01
Instrument: SVC HR-1024i

data=
350.0 0.0 0.0 0.15
360.0 0.0 0.0 0.16
370.0 0.0 0.0 0.17
380.0 0.0 0.0 0.18
"""
    sig_file = temp_dir / "test_sample.sig"
    sig_file.write_text(sig_content)
    return sig_file


@pytest.fixture
def sample_metadata_csv(temp_dir):
    """Create a sample metadata CSV file for testing."""
    csv_content = """FileNum,Date,Prefix,Subfolder
0,090923,HR,
1,090923,HR,
2,090923,HR,SubFolder1
"""
    csv_file = temp_dir / "metadata.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent


@pytest.fixture
def data_dir(project_root):
    """Get the data directory path."""
    return project_root / "data"
