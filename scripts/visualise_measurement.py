"""
Individual Measurement Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and plots all measurements on one graph.

Args:
    python visualise_measurement.py [input_csv] [-n output_name]
    [input_csv]: Optional path to the input CSV file. If omitted, uses the latest generated CSV in the output folder.
    The plot is always saved as a PNG and not shown interactively.
"""

from pathlib import Path

import load_data as ld
import numpy as np
import matplotlib.pyplot as plt
import sys
import json


def parse_cli_args(argv):
    """Parse command-line arguments, supporting -n/--name for the output file."""
    input_parts = []
    output_name = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ('-n', '--name'):
            if i + 1 >= len(argv):
                raise ValueError("Output name must be provided after -n or --name")
            output_name = argv[i + 1]
            i += 2
        else:
            input_parts.append(arg)
            i += 1
    input_path = None
    if input_parts:
        input_path_str = ' '.join(input_parts)
        input_path = Path(input_path_str.replace('\\', '/'))
    return input_path, output_name


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
    raw_input_path, output_name = parse_cli_args(sys.argv[1:])
    input_csv = None

    if raw_input_path:
        input_csv = Path(raw_input_path)
        candidate_paths = [
            Path.cwd() / input_csv,
            project_root / input_csv,
        ]
        if input_csv.parts and input_csv.parts[0] == project_root.name:
            candidate_paths.append(project_root.joinpath(*input_csv.parts[1:]))
        input_csv = next((p for p in candidate_paths if p.exists()), input_csv)
    else:
        input_csv = project_root / 'data' / 'output_data' / 'merged_spectral_data.csv'

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {input_csv}\n"
            "Please provide an absolute path or a valid relative path to the CSV file."
        )

    print(f"Loading spectral data from: {input_csv}")
    df = ld.load_spectral_data(input_csv)
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength points")

    output_file = (output_name if output_name else '_hyperspectral_') + '.png'
    output_image = project_root / 'data' / 'output_data' / output_file
    plot_all_measurements(df, output_image)

    adding_visuals_in_json(project_root, "Hyperspectral Data", "spectral", output_image)


if __name__ == "__main__":
    main()