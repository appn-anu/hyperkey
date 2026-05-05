"""
Individual Measurement Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and creates a plot of a single measurement.

Args:
    python visualise_measurement.py [measurement_name] [output_file]
    [measurement_name]: The name of the measurement to plot (from 'Name' column in CSV). Use 'all' to plot all measurements.
    [output_file]: Optional filename to save the plot image to output_data folder. If not provided, the plot will be displayed on screen.
"""

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

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
    else:
        plt.show()

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
    # Load spectral data
    project_root = ld.get_project_root()
    csv_path = project_root / 'data' / 'output_data' / 'merged_spectral_data.csv'
    
    df = ld.load_spectral_data(csv_path)
    
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength points")
    print(f"Available measurements: {df.index.tolist()}")
    
    # Get name from command line argument or prompt
    name = None
    file_name = None
    if len(sys.argv) >= 2:
        name = sys.argv[1]
    if len(sys.argv) >= 3:
        file_name = str(sys.argv[2]).strip()

    if name is None:
        name = input("Enter measurement name (or 'all' to plot everything): ").strip()

    if file_name is None:
        output_image = None
    else:
        output_image = project_root / 'data' / 'output_data' / (file_name +'.png')

    # Plot
    if name.lower() == "all":
        plot_all_measurements(df, output_image)
        if output_image is not None:
            adding_visuals_in_json(project_root=project_root, title="All spectral measurements", visual_type="spec_image", image_path=output_image)
    else:
        plot_measurement(df, name, output_image)
        if output_image is not None:
            adding_visuals_in_json(project_root=project_root, title="Spectral measurement", visual_type="spec_image", image_path=output_image)


if __name__ == "__main__":
    main()