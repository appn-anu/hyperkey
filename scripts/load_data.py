import pandas as pd
from pathlib import Path

def get_project_root():
    """Get the project root directory (parent of scripts folder)."""
    return Path(__file__).parent.parent


def is_valid_column(col_str):
    if col_str == "Name":
        return True
    try:
        float(col_str)
        return True
    except ValueError:
        return False


def load_spectral_data(csv_path):
    """Load the spectral data from CSV file."""
    # Read CSV, using 'Name' as the index
    df = pd.read_csv(csv_path, index_col='Name')
    
    # Filter to only keep valid numeric wavelength columns
    # Remove metadata columns and unnamed/empty columns
    cols_to_keep = []
    for col in df.columns:
        col_str = str(col).strip()
        # Skip non-numeric columns (metadata) and empty/unnamed columns

        if is_valid_column(col_str):
            # Check if it's a valid float (single wavelength number)
            try:
                float(col_str)
                cols_to_keep.append(col)
            except ValueError:
                pass
    df = df[cols_to_keep]

    return df