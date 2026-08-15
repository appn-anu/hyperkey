"""
Individual Measurement Visualisation Script
Reads hyperspectral data from merged_spectral_data.csv and plots all measurements on one graph.

Args:
    python visualise_measurement.py [input_csv] [-n output_name]
    [input_csv]: Optional path to the input CSV file. If omitted, uses the latest generated CSV in the output folder.
    The plot is always saved as a PNG and not shown interactively.
"""

import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath

import app_paths

# Must run before pyplot is imported: selects the Agg backend and points
# matplotlib's config/font cache somewhere writable on Android.
app_paths.configure_matplotlib()

import load_data as ld
import numpy as np
import matplotlib.pyplot as plt
import json


def resolve_output_path(output_value, default_directory, default_filename, extension='.png'):
    """Resolve an output name or path into a full file path."""
    default_directory = Path(default_directory)

    if output_value is None:
        output_path = default_directory / f"{default_filename}{extension}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    raw_value = str(output_value).strip().strip('"').strip("'")
    if not raw_value:
        raise ValueError("Output value cannot be empty.")

    windows_value = PureWindowsPath(raw_value)
    posix_value = PurePosixPath(raw_value)
    has_directory = (
        "/" in raw_value
        or "\\" in raw_value
        or bool(windows_value.drive)
        or str(posix_value.parent) not in ("", ".")
    )

    output_path = Path(raw_value).expanduser()
    if has_directory:
        if output_path.suffix:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path
        output_path = output_path.with_suffix(extension)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    if output_path.suffix:
        output_path = default_directory / output_path.name
    else:
        output_path = default_directory / f"{output_path.name}{extension}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def parse_cli_args(argv):
    """Parse command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Generate a spectral measurement plot from merged hyperspectral data."
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        help="Optional input merged spectral CSV file. Defaults to the merged output CSV.",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="output_name",
        help="Output image name prefix or optional output path.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_name",
        help="Output image name prefix or optional output path.",
    )
    args = parser.parse_args(argv)
    input_path = Path(args.input_csv) if args.input_csv else None
    return input_path, args.output_name


def plot_all_measurements(df, output_path=None, dark_mode=True):
    """
    Plot all measurements on one graph.
    
    Args:
        df: DataFrame containing spectral data
        output_path: Optional path to save the plot
    """
    wavelengths = np.array([float(col) for col in df.columns])
    values = df.to_numpy(dtype=float)
    mean_values = np.nanmean(values, axis=0)
    std_values = np.nanstd(values, axis=0)
    upper_bound = mean_values + (2 * std_values)
    lower_bound = mean_values - (2 * std_values)

    if dark_mode:
        plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))

    ribbon_color = 'lightblue' if dark_mode else 'skyblue'
    ax.fill_between(
        wavelengths,
        lower_bound,
        upper_bound,
        color=ribbon_color,
        alpha=0.25,
        zorder=1,
    )

    for name, row in df.iterrows():
        intensities = row.values.astype(float)
        ax.plot(wavelengths, intensities, linewidth=1, alpha=0.6, label=name, zorder=2)

    ax.set_xlabel('Wavelength (nm)', fontsize=12)
    ax.set_ylabel('Reflectance (%)', fontsize=12)
    ax.set_title('All Spectral Measurements', fontsize=14)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    # Optional: remove legend if too many lines
    if len(df) <= 20:
        ax.legend()

    if output_path is None:
        raise ValueError("Output path must be provided to save the plot as a PNG.")

    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")
    plt.close(fig)

def adding_visuals_in_json(summary_path, title, visual_type, image_path):
    """Append a visualisation entry to the summary.json the pipeline wrote."""
    json_path = (
        Path(summary_path)
        if summary_path is not None
        else app_paths.default_output_directory() / "summary.json"
    )
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


def main(
    input_path=None,
    output_name=None,
    dark_mode=True,
    output_directory=None,
    summary_path=None,
):
    project_root = ld.get_project_root()

    output_dir = (
        Path(output_directory)
        if output_directory is not None
        else app_paths.default_output_directory()
    )

    if summary_path is None:
        summary_path = output_dir / "summary.json"

    if input_path is None and output_name is None:
        cli_input_path, cli_output_name = parse_cli_args(None)

    raw_input_path = Path(input_path) if input_path is not None else cli_input_path
    output_name = output_name if output_name is not None else cli_output_name
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
        # The pipeline always date-stamps the merged CSV, so fall back to the
        # most recent one in the output directory rather than a fixed name.
        candidates = sorted(
            output_dir.glob("*merged_spectral_data_*.csv"),
            key=lambda p: p.stat().st_mtime,
        )
        input_csv = candidates[-1] if candidates else output_dir / "merged_spectral_data.csv"

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {input_csv}\n"
            "Please provide an absolute path or a valid relative path to the CSV file."
        )

    print(f"Loading spectral data from: {input_csv}")
    df = ld.load_spectral_data(input_csv)
    print(f"Loaded {len(df)} measurements with {len(df.columns)} wavelength points")

    output_image = resolve_output_path(output_name, output_dir, '_hyperspectral_')
    plot_all_measurements(df, output_image, dark_mode)

    adding_visuals_in_json(summary_path, "Hyperspectral Data", "spectral", output_image)


if __name__ == "__main__":
    main()