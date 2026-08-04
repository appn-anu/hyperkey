"""
Heatmap Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and creates a heatmap of a spectral index
arranged in a grid as close to square as possible.

Args:
    python visualise_heatmap.py [input_csv] [-l location_file] [-n output_name]
        [-i index_name]

Options:
    -l, --location    Location file for grid placement.
    -n, --name        Output image name prefix.
    -i, --index       Spectral index name to compute (default: NDVI).
"""

from pathlib import Path
import argparse

import load_data as ld
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import spyndex
import json


def find_closest_wavelength(wavelengths, target):
    """Find the wavelength closest to the target value."""
    wavelengths = wavelengths.astype(float)
    idx = np.abs(wavelengths - target).argmin()
    return idx, wavelengths[idx]


def calculate_spectral_index(df, index_name='NDVI', red_wavelength=670.0, nir_wavelength=800.0):
    """
    Calculate a spectral index using spyndex.
    Default index is NDVI, calculated from the closest Red and NIR wavelengths.
    """
    index_name = str(index_name).upper().strip()
    wavelengths = df.columns.astype(float)

    red_idx, matched_red = find_closest_wavelength(wavelengths, red_wavelength)
    nir_idx, matched_nir = find_closest_wavelength(wavelengths, nir_wavelength)

    red = df.iloc[:, red_idx]
    nir = df.iloc[:, nir_idx]

    print(f"Using Red band: {matched_red:.1f}nm (index {red_idx})")
    print(f"Using NIR band: {matched_nir:.1f}nm (index {nir_idx})")

    params = {
        "N": nir,
        "R": red
    }

    try:
        result = spyndex.computeIndex(index=index_name, params=params, returnOrigin=True)
    except Exception as e:
        raise ValueError(
            f"Failed to compute index '{index_name}' with Red/NIR bands. "
            f"Please verify the index name and available bands. Original error: {e}"
        )

    values = np.asarray(result).flatten()
    return values


def calculate_square_grid(n_measurements):
    """
    Calculate the best square-ish grid dimensions for the heatmap.
    Returns (rows, cols) where rows * cols >= n_measurements and is as close to square as possible.
    """
    # Start with the square root
    side = int(np.ceil(np.sqrt(n_measurements)))
    
    # Try to make it as square as possible
    # First try: rows = side, cols = side (might have extra cells)
    # If that's too wide, try: rows = side, cols = side - 1
    
    best_rows = side
    best_cols = side
    
    # Calculate the difference from square
    diff = (best_rows * best_cols) - n_measurements
    
    # Try decreasing columns if that gives a better fit
    if side > 1:
        diff_alt = (side * (side - 1)) - n_measurements
        if 0 <= diff_alt < diff:
            best_cols = side - 1
    
    return best_rows, best_cols


def validate_row_range_columns(csv_path):
    """
    Check if CSV contains 'row' and 'range' columns (case-insensitive) and validate them.
    Returns (rows_list, ranges_list) if valid, (None, None) if columns don't exist.
    Raises ValueError if columns exist but contain non-integer values.
    """
    # Load data without setting index first to check columns properly
    raw_df = pd.read_csv(csv_path)
    
    # Case-insensitive column lookup
    cols_lower = {col.lower(): col for col in raw_df.columns}
    
    has_row = 'row' in cols_lower
    has_range = 'range' in cols_lower
    
    # If neither exists, return None and use square grid
    if not has_row and not has_range:
        return None, None
    
    # If only one exists, that's an error
    if has_row != has_range:
        missing = 'range' if has_row else 'row'
        raise ValueError(f"Found 'row' column but missing '{missing}' column. Both must exist together.")
    
    # Both columns exist - validate them strictly
    row_col = cols_lower['row']
    range_col = cols_lower['range']
    
    try:
        row_vals = pd.to_numeric(raw_df[row_col], errors='coerce')
        range_vals = pd.to_numeric(raw_df[range_col], errors='coerce')
        
        if row_vals.isna().any() or range_vals.isna().any():
            raise ValueError("Found non-numeric values in 'row' or 'range' columns")
        
        # Check if all values are integers
        if not (row_vals == row_vals.astype(int)).all() or not (range_vals == range_vals.astype(int)).all():
            raise ValueError("All values in 'row' and 'range' columns must be integers")
        
        return row_vals.astype(int).tolist(), range_vals.astype(int).tolist()
    
    except ValueError as e:
        raise ValueError(f"Error validating row/range columns: {e}")


def parse_location_grid(grid_df, measurement_names):
    """Parse a headerless grid location file into mapping of measurement -> (row, col)."""
    location_mapping = {}
    duplicate_measurements = []

    for i, row in enumerate(grid_df.itertuples(index=False, name=None)):
        for j, cell in enumerate(row):
            if pd.isna(cell) or str(cell).strip() == '':
                continue
            measurement = str(cell).strip()
            if measurement in location_mapping:
                duplicate_measurements.append(measurement)
            location_mapping[measurement] = (i + 1, j + 1)

    if duplicate_measurements:
        duplicates = ', '.join(sorted(set(duplicate_measurements)))
        raise ValueError(
            f"Duplicate measurement names found in location file: {duplicates}. "
            "Each measurement must appear only once."
        )

    # Filter to only include measurements that are in the location file
    filtered_mapping = {m: location_mapping[m] for m in measurement_names if m in location_mapping}
    
    missing_measurements = [m for m in measurement_names if m not in location_mapping]
    if missing_measurements:
        print(
            f"Warning: {len(missing_measurements)} measurement(s) not found in location file. "
            f"They will be excluded from the heatmap. Missing: "
            f"{missing_measurements[:5]}{'...' if len(missing_measurements) > 5 else ''}"
        )

    return filtered_mapping


def load_location_mapping(location_path, measurement_names):
    """Load a location file and map each measurement name to a grid coordinate."""
    location_df = pd.read_csv(location_path, header=0)
    cols_lower = {col.lower(): col for col in location_df.columns}

    if 'row' in cols_lower and 'range' in cols_lower:
        row_col = cols_lower['row']
        range_col = cols_lower['range']

        row_vals = pd.to_numeric(location_df[row_col], errors='coerce')
        range_vals = pd.to_numeric(location_df[range_col], errors='coerce')

        if row_vals.isna().any() or range_vals.isna().any():
            raise ValueError("Found non-numeric values in location file 'row' or 'range' columns")

        if not (row_vals == row_vals.astype(int)).all() or not (range_vals == range_vals.astype(int)).all():
            raise ValueError("All values in location file 'row' and 'range' columns must be integers")

        row_vals = row_vals.astype(int)
        range_vals = range_vals.astype(int)

        # Filter to only include measurements that are in the location file
        filtered_mapping = {
            measurement: (row_vals.loc[measurement], range_vals.loc[measurement])
            for measurement in measurement_names if measurement in location_df.index
        }
        
        missing_measurements = [m for m in measurement_names if m not in location_df.index]
        if missing_measurements:
            print(
                f"Warning: {len(missing_measurements)} measurement(s) not found in location file. "
                f"They will be excluded from the heatmap. Missing: "
                f"{missing_measurements[:5]}{'...' if len(missing_measurements) > 5 else ''}"
            )

        extra_measurements = [m for m in location_df.index if m not in measurement_names]
        if extra_measurements:
            print(
                f"Warning: location file contains {len(extra_measurements)} extra measurement(s) not found in spectral data. "
                f"They will be ignored. Example: {extra_measurements[:5]}{'...' if len(extra_measurements) > 5 else ''}"
            )

        return filtered_mapping

    # Fallback: treat the file as a headerless grid
    location_df = pd.read_csv(location_path, header=None)
    return parse_location_grid(location_df, measurement_names)


def parse_cli_args(argv):
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Generate a spectral index heatmap from merged hyperspectral data."
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        help="Optional input merged spectral CSV file. Defaults to data/output_data/merged_spectral_data.csv.",
    )
    parser.add_argument(
        "-l",
        "--location",
        dest="location_path",
        help="Location file for grid placement.",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="output_name",
        help="Output image name prefix.",
    )
    parser.add_argument(
        "-i",
        "--index",
        dest="index_name",
        default="NDVI",
        help="Spectral index name to compute (default: NDVI).",
    )
    args = parser.parse_args(argv)
    input_path = Path(args.input_csv) if args.input_csv else None
    return input_path, args.location_path, args.output_name, args.index_name


def organize_grid_by_location(visual_values, measurement_names, location_mapping):
    """Organize grid according to a provided location mapping."""
    max_row = max(row for row, _ in location_mapping.values())
    max_col = max(col for _, col in location_mapping.values())
    rows = max_row
    cols = max_col
    
    grid = np.full((rows, cols), np.nan)
    position_to_idx = {}
    duplicates = []
    
    for idx, measurement in enumerate(measurement_names):
        row, col = location_mapping[measurement]
        r = row - 1
        c = col - 1
        if not np.isnan(grid[r, c]):
            duplicates.append((row, col))
        grid[r, c] = visual_values[idx]
        position_to_idx[(r, c)] = idx
    
    if duplicates:
        duplicates_summary = ', '.join(f"({r},{c})" for r, c in sorted(set(duplicates)))
        print(
            f"Warning: duplicate location coordinates found at {len(duplicates)} position(s). "
            "Most recent measurements were used for these locations: "
            f"{duplicates_summary}"
        )
    
    return grid, rows, cols, position_to_idx


def organize_grid_by_row_range(visual_values, rows_list, ranges_list):
    """
    Organize grid according to specified row and range values (1-indexed).
    Returns (grid, rows, cols) where grid is organized by row/range.
    """
    rows = max(rows_list)
    cols = max(ranges_list)
    
    grid = np.full((rows, cols), np.nan)
    duplicates = []
    
    for idx, (row, range_idx) in enumerate(zip(rows_list, ranges_list)):
        if idx < len(visual_values):
            r = row - 1
            c = range_idx - 1
            if not np.isnan(grid[r, c]):
                duplicates.append((row, range_idx))
            grid[r, c] = visual_values[idx]  # Convert to 0-indexed
    
    if duplicates:
        duplicates_summary = ', '.join(f"({r},{c})" for r, c in sorted(set(duplicates)))
        print(
            f"Warning: duplicate row/range coordinates found at {len(duplicates)} position(s). "
            "Most recent measurements were used for these locations: "
            f"{duplicates_summary}"
        )
    
    return grid, rows, cols


def create_heatmap(visual_type, visual_values, measurement_names, output_path=None, location_mapping=None, rows_list=None, ranges_list=None):
    """
    Create a heatmap of specified values.
    If location_mapping is provided, organize grid by location file.
    If rows_list and ranges_list are provided, organize grid by row/range.
    Otherwise, organize in a square-ish grid.
    """
    n_measurements = len(visual_values)
    position_to_idx = None
    
    # Determine grid dimensions and organize values
    if location_mapping is not None:
        grid, rows, cols, position_to_idx = organize_grid_by_location(
            visual_values, measurement_names, location_mapping
        )
        print(f"\nGrid dimensions: {rows} x {cols} (organized by location file)")
    elif rows_list is not None and ranges_list is not None:
        grid, rows, cols = organize_grid_by_row_range(visual_values, rows_list, ranges_list)
        print(f"\nGrid dimensions: {rows} x {cols} (organized by row/range metadata)")
    else:
        # Calculate optimal grid dimensions
        rows, cols = calculate_square_grid(n_measurements)
        print(f"\nGrid dimensions: {rows} x {cols} = {rows * cols} cells for {n_measurements} measurements")
        
        # Create grid (pad with NaN if needed)
        grid = np.full(rows * cols, np.nan)
        grid[:n_measurements] = visual_values
        grid = grid.reshape(rows, cols)
    
    # Create the heatmap
    _, ax = plt.subplots(figsize=(10, 8))
    
    # Create heatmap with a good colormap for NDVI
    # NDVI ranges from -1 to 1, so we use a diverging colormap
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-1, vmax=1, aspect='equal')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, label=visual_type)
    cbar.ax.tick_params(labelsize=10)
    
    # Set labels
    ax.set_title(f'{visual_type} Heatmap ({rows}x{cols} grid)', fontsize=14, fontweight='bold')
    
    # Remove axis ticks and labels for clean grid look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    
    # Add measurement names as text in each cell
    for i in range(rows):
        for j in range(cols):
            if position_to_idx is not None:
                cell_idx = position_to_idx.get((i, j))
            elif rows_list is not None and ranges_list is not None:
                # For row/range organized grid, find which measurement is at this position
                # Note: row/range are 1-indexed, so convert back to 1-indexed for comparison
                cell_idx = None
                for idx, (row, range_idx) in enumerate(zip(rows_list, ranges_list)):
                    if row - 1 == i and range_idx - 1 == j:
                        cell_idx = idx
                        break
            else:
                cell_idx = i * cols + j
            
            if cell_idx is not None and cell_idx < n_measurements:
                # Get short name from measurement
                name = measurement_names[cell_idx]
                # Extract just the number part for display
                short_name = name.replace('HR.032426.', '').replace('.sig', '')
                text_color = 'white' if grid[i, j] < 0 or grid[i, j] > 0.7 else 'black'
                ax.text(j, i, short_name, ha='center', va='center', 
                       fontsize=8, color=text_color, fontweight='bold')
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Heatmap saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()
    
    return grid

def adding_visuals_in_json(project_root, title, visual_type, image_path):
    json_path = project_root / "data" / "output_data" / "summary.json"
    if not json_path.exists():
        raise FileNotFoundError(f"summary.json not found at {json_path}")
    
    with open(json_path, "r") as f:
        summary = json.load(f)

    if "visualisations" not in summary:
        summary["visualisations"] = []
    image_name = Path(image_path).name
    new_entry = {
        "title": title,
        "type": visual_type,
        "path": image_name
    } 

    summary["visualisations"].append(new_entry)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=4)


def main(input_path=None, raw_location_path=None, output_name=None, index_name=None):
    # Get project root and use relative paths
    project_root = ld.get_project_root()
    location_mapping = None

    if input_path is None and raw_location_path is None and output_name is None and index_name is None:
        cli_input_path, cli_location_path, cli_output_name, cli_index_name = parse_cli_args(None)

    raw_input_path = Path(input_path) if input_path is not None else cli_input_path
    raw_location_path = raw_location_path if raw_location_path is not None else cli_location_path
    output_name = output_name if output_name is not None else cli_output_name
    index_name = index_name if index_name is not None else cli_index_name
    red_wavelength = 670.0
    nir_wavelength = 800.0

    if output_name is None:
        output_name = '_heatmap_'

    if raw_input_path:
        input_csv = Path(raw_input_path)
        if not input_csv.exists():
            candidate_paths = [
                Path.cwd() / raw_input_path,
                project_root / raw_input_path,
            ]
            if input_csv.parts and input_csv.parts[0] == project_root.name:
                candidate_paths.append(project_root.joinpath(*input_csv.parts[1:]))
            input_csv = next((p for p in candidate_paths if p.exists()), input_csv)
    else:
        input_csv = project_root / 'data' / 'output_data' / 'merged_spectral_data.csv'

    output_image = project_root / 'data' / 'output_data' / (output_name + '.png')

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {input_csv}\n"
            "Please provide an absolute path, or a valid relative path from this folder. Example:\n"
            "  python visualise_heatmap.py \"C:/Users/.../hyperkey/data/raw_data/SVC sample files/sample-combined-file.csv\"\n"
            "You can also use a project-relative path from the scripts folder:\n"
            "  python visualise_heatmap.py \"data/raw_data/SVC sample files/sample-combined-file.csv\""
        )
    
    print("Loading spectral data...")
    df = ld.load_spectral_data(input_csv)
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength bands")
    
    rows_list = None
    ranges_list = None
    try:
        if raw_location_path:
            location_csv = Path(raw_location_path)
            if not location_csv.exists():
                candidate_paths = [
                    Path.cwd() / raw_location_path,
                    project_root / raw_location_path,
                ]
                if location_csv.parts and location_csv.parts[0] == project_root.name:
                    candidate_paths.append(project_root.joinpath(*location_csv.parts[1:]))
                location_csv = next((p for p in candidate_paths if p.exists()), location_csv)

            if not location_csv.exists():
                raise FileNotFoundError(f"Location file not found: {location_csv}")

            print(f"Loading location file: {location_csv}")
            location_mapping = load_location_mapping(location_csv, df.index.tolist())
            print("Using location file ordering for grid placement.")
        else:
            rows_list, ranges_list = validate_row_range_columns(input_csv)
            if rows_list is not None:
                print("Found valid 'row' and 'range' columns - will organize grid by coordinates")
    except ValueError as e:
        print(f"Error: {e}")
        raise
    
    print(f"\nCalculating {index_name}...")
    ndvi_values = calculate_spectral_index(df, index_name, red_wavelength, nir_wavelength)
    
    # Print summary statistics
    print(f"\nStatistics for {index_name}:")
    print(f"  Min: {np.nanmin(ndvi_values):.4f}")
    print(f"  Max: {np.nanmax(ndvi_values):.4f}")
    print(f"  Mean: {np.nanmean(ndvi_values):.4f}")
    print(f"  Std: {np.nanstd(ndvi_values):.4f}")
    
    # Create heatmap
    print("\nCreating heatmap...")
    if location_mapping is not None:
        # Filter data to only include measurements present in location mapping
        included_measurements = list(location_mapping.keys())
        included_indices = [df.index.tolist().index(m) for m in included_measurements]
        filtered_ndvi = ndvi_values[included_indices]
        filtered_names = included_measurements
        print(f"Using {len(included_measurements)} measurements found in location file.")
    else:
        filtered_ndvi = ndvi_values
        filtered_names = df.index.tolist()
    
    create_heatmap(
        index_name,
        filtered_ndvi,
        filtered_names,
        output_image,
        location_mapping=location_mapping,
        rows_list=rows_list,
        ranges_list=ranges_list,
    )

    adding_visuals_in_json(project_root, f"{index_name} Heatmap", "heatmap", output_image)
    
    print("\nDone!")


if __name__ == '__main__':
    main()