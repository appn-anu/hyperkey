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