"""
Individual Measurement Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and plots all measurements on one graph.

Args:
    python visualise_measurement.py [input_csv]
    [input_csv]: Optional path to the input CSV file. If omitted, uses the default merged_spectral_data.csv file.
    The plot is always saved as a PNG and not shown interactively.
"""

from pathlib import Path

import load_data as ld
import numpy as np
import matplotlib.pyplot as plt
import sys
import json
from pathlib import Path


# python visualise_measurement.py all all_spectral_measurements
# python visualise_measurement.py "HCN1" hcn1_grap

def plot_measurement(df, name, output_path=None):
    """
    Plot a single measurement given a Name.
    
    Args:
        df: DataFrame containing spectral data
        name: The measurement name from the 'Name' column
        output_path: Optional path to save the plot
    """
    if name not in df.index:
        available_names = df.index.tolist()
        raise ValueError(f"Measurement '{name}' not found. Available names: {available_names}")
    
    # Get the data for this measurement
    row = df.loc[name]
    
    # Get wavelengths (column names) and convert to float
    wavelengths = np.array([float(col) for col in df.columns])
    intensities = row.values.astype(float)
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(wavelengths, intensities, 'b-', linewidth=1)
    plt.xlabel('Wavelength (nm)', fontsize=12)
    plt.ylabel('Reflectance (%)', fontsize=12)
    plt.title(f'Spectral Measurement: {name}', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_all_measurements(df, output_path=None):
    """
    Plot all measurements on one graph.
    
    Args:
        df: DataFrame containing spectral data
        output_path: Optional path to save the plot
    """
    wavelengths = np.array([float(col) for col in df.columns])

    plt.figure(figsize=(12, 6))

    for name, row in df.iterrows():
        intensities = row.values.astype(float)
        plt.plot(wavelengths, intensities, linewidth=1, alpha=0.6, label=name)

    plt.xlabel('Wavelength (nm)', fontsize=12)
    plt.ylabel('Reflectance (%)', fontsize=12)
    plt.title('All Spectral Measurements', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Optional: remove legend if too many lines
    if len(df) <= 20:
        plt.legend()

    if output_path is None:
        raise ValueError("Output path must be provided to save the plot as a PNG.")

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    plt.close()

def adding_visuals_in_json(project_root, title, visual_type, image_path):
    json_path = project_root / "data" / "output_data" / "summary.json"
    if not json_path.exists():
        raise FileNotFoundError(f"summary.json not found at {json_path}")
    
    with open(json_path, "r") as f:
        summary = json.load(f)

    if "spectral_image" not in summary:
        summary["spectral_image"] = []
    image_name = Path(image_path).name
    new_entry = {
        "title": title,
        "type": visual_type,
        "path": image_name
    } 

    summary["spectral_image"].append(new_entry)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=4)


def main():
    project_root = ld.get_project_root()
    input_csv = None

    if len(sys.argv) > 1:
        input_csv = Path(' '.join(sys.argv[1:]))
        candidate_paths = [
            Path.cwd() / input_csv,
            project_root / input_csv,
        ]
        if input_csv.parts and input_csv.parts[0] == project_root.name:
            candidate_paths.append(project_root.joinpath(*input_csv.parts[1:]))
        input_csv = next((p for p in candidate_paths if p.exists()), input_csv)

    if input_csv is None:
        input_csv = project_root / 'data' / 'output_data' / 'merged_spectral_data.csv'

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {input_csv}\n"
            "Please provide an absolute path or a valid relative path to the CSV file."
        )

    print(f"Loading spectral data from: {input_csv}")
    df = ld.load_spectral_data(input_csv)
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength points")

    output_image = project_root / 'data' / 'output_data' / 'hyperspectral.png'
    plot_all_measurements(df, output_image)


if __name__ == "__main__":
    main()