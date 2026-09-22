"""Tests for heatmap coordinate parsing."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from visualise_heatmap import validate_row_range_columns


def test_validate_row_col_columns(tmp_path):
    csv_path = tmp_path / "spectral.csv"
    pd.DataFrame({"row": [1, 2], "col": [3, 4]}).to_csv(csv_path, index=False)

    assert validate_row_range_columns(csv_path) == ([1, 2], [3, 4])


def test_validate_row_range_columns_still_supported(tmp_path):
    csv_path = tmp_path / "spectral.csv"
    pd.DataFrame({"row": [1, 2], "range": [3, 4]}).to_csv(csv_path, index=False)

    assert validate_row_range_columns(csv_path) == ([1, 2], [3, 4])


def test_validate_row_without_coordinate_column_raises(tmp_path):
    csv_path = tmp_path / "spectral.csv"
    pd.DataFrame({"row": [1, 2], "value": [3, 4]}).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="range.*col"):
        validate_row_range_columns(csv_path)