#!/usr/bin/env python3

# Example:
# python scripts/pipeline.py data/example_data/example1/metadata.csv -r "data\example_data\example1"
# python scripts/pipeline.py data/example_data/example1/metadata.csv -r "data\example_data\example1" -o data\TestHyperKey\sydneyAPPN
# python scripts/pipeline.py data/example_data/example1/metadata.csv -r "data\example_data\example1" -l "data\raw_location\species_locations.csv"
# python scripts/pipeline.py data/example_data/example1/metadata.csv -r "data\example_data\example1" -d
# python scripts/pipeline.py data/example_data/example1/metadata.csv -r "data\example_data\example1" --outlier-analysis
# python scripts/pipeline.py -h

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


# ---------------------------
# Helpers and Formatting
# ---------------------------

def get_log_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_stamp():
    return datetime.now().strftime("%d%m%Y")


def build_output_names(custom_prefix=None):
    """Build the existing dated names for all generated outputs."""
    date_stamp = get_date_stamp()

    if custom_prefix:
        merged_output_name = f"{custom_prefix}_merged_spectral_data_{date_stamp}"
        heatmap_output_name = f"{custom_prefix}_heatmap_{date_stamp}"
        spectral_graph_output_name = f"{custom_prefix}_SpectralGraph_{date_stamp}"
        report_output_name = f"{custom_prefix}_report_{date_stamp}"
        outlier_output_name = f"{custom_prefix}_outlier_analysis_{date_stamp}"
    else:
        merged_output_name = f"merged_spectral_data_{date_stamp}"
        heatmap_output_name = f"heatmap_{date_stamp}"
        spectral_graph_output_name = f"SpectralGraph_{date_stamp}"
        report_output_name = f"report_{date_stamp}"
        outlier_output_name = f"outlier_analysis_{date_stamp}"

    return {
        "merged_output_name": merged_output_name,
        "heatmap_output_name": heatmap_output_name,
        "spectral_graph_output_name": spectral_graph_output_name,
        "report_output_name": report_output_name,
        "outlier_output_name": outlier_output_name
    }

def create_argument_parser():
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract and merge spectral data from metadata CSV files and .sig files. "
            "After creating the merged CSV, run the visualisation and report modules "
            "sequentially."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  py hyperkey.py
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 -n sydneyAPPN
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 -o "D:\Results\WheatData"
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 -o "D:\Results\WheatData" -n sydneyAPPN
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 -l data\raw_location\species_locations.csv
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 -d
  py hyperkey.py data\example_data\example1\metadata.csv -r data\example_data\example1 --outlier-analysis

Output naming:
  Default:
    data/output_data/merged_spectral_data_DDMMYYYY.csv
    data/output_data/heatmap_DDMMYYYY
    data/output_data/SpectralGraph_DDMMYYYY
    data/output_data/report_DDMMYYYY.md / .html / .pdf

  With -n sydneyAPPN:
    data/output_data/sydneyAPPN_merged_spectral_data_DDMMYYYY.csv
    data/output_data/sydneyAPPN_heatmap_DDMMYYYY
    data/output_data/sydneyAPPN_SpectralGraph_DDMMYYYY
    data/output_data/sydneyAPPN_report_DDMMYYYY.md / .html / .pdf

  With -o "D:\Results\WheatData":
    D:/Results/WheatData/merged_spectral_data_DDMMYYYY.csv
    D:/Results/WheatData/heatmap_DDMMYYYY
    D:/Results/WheatData/SpectralGraph_DDMMYYYY
    D:/Results/WheatData/report_DDMMYYYY.md / .html / .pdf

  With -o "D:\Results\WheatData" -n sydneyAPPN:
    D:/Results/WheatData/sydneyAPPN_merged_spectral_data_DDMMYYYY.csv
    D:/Results/WheatData/sydneyAPPN_heatmap_DDMMYYYY
    D:/Results/WheatData/sydneyAPPN_SpectralGraph_DDMMYYYY
    D:/Results/WheatData/sydneyAPPN_report_DDMMYYYY.md / .html / .pdf
"""
    )

    parser.add_argument(
        "metadata_files",
        metavar="METADATA_CSV",
        nargs="*",
        help=(
            "One or more metadata CSV files. If omitted, the interactive "
            "selection menu is shown."
        )
    )

    parser.add_argument(
        "-r",
        "--root",
        dest="root",
        default=None,
        metavar="ROOT_FOLDER",
        help=(
            "Root folder containing the .sig files. If omitted while metadata "
            "files are supplied, the current directory is used."
        )
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        metavar="OUTPUT_DIRECTORY",
        help=(
            "Optional directory where all generated outputs will be saved. "
            "If omitted, data/output_data is used."
        )
    )

    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        default=None,
        metavar="OUTPUT_NAME",
        help=(
            "Optional prefix for generated output filenames. For example, "
            "-n sydneyAPPN creates sydneyAPPN_merged_spectral_data_DDMMYYYY.csv."
        )
    )

    parser.add_argument(
        "-l",
        "--raw-location-path",
        dest="raw_location_path",
        default=None,
        metavar="RAW_LOCATION_FILE",
        help=(
            "Optional path to the input file containing species location data. "
            "This file is passed to visualise_heatmap.py."
        )
    )

    parser.add_argument(
        "-d",
        "--dark",
        dest="dark_mode",
        action="store_false",
        default=True,
        help=(
            "Disable dark mode for generated outputs. Dark mode is enabled be default."
            "Just -d and no value is needed after that." 
            "This flag is passed to visualise_heatmap.py, visualise_measurement.py, and report.py. "
            "by default dark_mode = True;"
            "Supplying this flag passes dark_mode=False. just -d and no value is needed after that."
        )
    )


    parser.add_argument(
        "--outlier-analysis",
        dest="outlier_analysis",
        action="store_true",
        default=False,
        help=(
            "Run outlier analysis after the merged spectral CSV is created. "
            "The flag does not require a value."
        )
    )

    return parser


def select_from_list(items, prompt_label):
    print(f"\n--- Select {prompt_label} ---")
    print("[0] ENTER MANUALLY / TYPE PATH")

    for i, item in enumerate(items, 1):
        print(f"[{i}] {item}")

    while True:
        choice = input(f"Enter number (0-{len(items)}): ").strip()

        if choice == "0":
            manual_val = input(f"Type the manual value for {prompt_label}: ").strip()

            if manual_val:
                return manual_val

            print("Input cannot be empty.")
            continue

        if choice.isdigit():
            idx = int(choice) - 1

            if 0 <= idx < len(items):
                return items[idx]

        print(f"Invalid selection. Please enter 0 or 1-{len(items)}. Press Ctrl+C to exit.")


def is_valid_filenum(val):
    if val is None:
        return False

    val = str(val).strip()
    return val.isdigit() and 0 <= int(val) <= 9999


def format_filenum(val):
    try:
        return str(int(val)).zfill(4)
    except Exception:
        return val


def normalise_subfolder(subfolder):
    subfolder = str(subfolder or "").strip()

    if subfolder in (".", "./", ".\\"):
        return ""

    return subfolder


def build_filepath(root, subfolder, prefix, date, filenum):
    root_path = Path(root)
    subfolder = normalise_subfolder(subfolder)
    padded_f = format_filenum(filenum)
    filename = f"{prefix}.{date}.{padded_f}.sig"

    if subfolder:
        return root_path / subfolder / filename

    return root_path / filename


def make_relative_path(path, start):
    """
    Return path relative to start where possible.

    This is a pathlib-based replacement for os.path.relpath in this pipeline.
    """
    path = Path(path)
    start = Path(start)

    try:
        return path.relative_to(start)
    except ValueError:
        pass

    try:
        return path.resolve().relative_to(start.resolve())
    except ValueError:
        return path


def parse_sig_file(filepath):
    wavelengths = []
    reflectance = []
    data_section = False
    filepath = Path(filepath)

    try:
        if not filepath.exists():
            return None, None

        with filepath.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()

                if line == "data=":
                    data_section = True
                    continue

                if data_section and line:
                    parts = line.split()

                    if len(parts) >= 4:
                        wavelengths.append(parts[0])
                        reflectance.append(parts[3])

        return wavelengths, reflectance

    except Exception:
        return None, None



# ---------------------------
# Main Logic
# ---------------------------

def main(cli_arguments=None):
    """
    Run the extraction and merge stage.

    cli_arguments:
        None     -> argparse reads arguments from the command line.
        list     -> argparse parses the supplied list, which is useful for tests
                    or for calling pipeline.main([...]) from another module.
    """
    parser = create_argument_parser()
    args = parser.parse_args(cli_arguments)

    # ---------------------------
    # 1. Setup Output Directory and Paths
    # ---------------------------

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent


    default_dir = project_root / "data" / "output_data"

    custom_prefix = str(args.name).strip() if args.name else None
    if custom_prefix == "":
        custom_prefix = None

    output_directory = (
        Path(args.output).expanduser()
        if args.output
        else default_dir
    )

    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Unable to create output directory '{output_directory}': {e}")
        return None

    output_names = build_output_names(custom_prefix=custom_prefix)

    merged_output_name = output_names["merged_output_name"]
    heatmap_output_name = output_names["heatmap_output_name"]
    spectral_graph_output_name = output_names["spectral_graph_output_name"]
    report_output_name = output_names["report_output_name"]
    outlier_output_name = output_names["outlier_output_name"]

    output_csv = output_directory / f"{merged_output_name}.csv"
    heatmap_output_path = output_directory / heatmap_output_name
    spectral_graph_output_path = output_directory / spectral_graph_output_name
    report_markdown_output_path = output_directory / f"{report_output_name}.md"
    report_html_output_path = output_directory / f"{report_output_name}.html"
    report_pdf_output_path = output_directory / f"{report_output_name}.pdf"
    outlier_output_path = output_directory / outlier_output_name

    raw_location_path = None
    if args.raw_location_path:
        raw_location_path = Path(args.raw_location_path).expanduser()

    log_path = output_directory / "error_log.txt"
    summary_path = output_directory / "summary.json"
    # ---------------------------
    # 2. Selection Phase
    # ---------------------------

    metadata_files = [Path(mf) for mf in args.metadata_files]
    root_folder = Path(".")

    processed_dir = project_root / "data" / "processed_data"
    raw_dir = project_root / "data" / "raw_data"

    if not metadata_files:
        search_csv_path = processed_dir if processed_dir.exists() else Path(".")

        csv_files = sorted(
            [
                item
                for item in search_csv_path.iterdir()
                if item.is_file() and item.suffix.lower() == ".csv"
            ]
        )

        selected_csv = select_from_list(csv_files, "Metadata CSV")

        if not selected_csv:
            return None

        metadata_files = [Path(selected_csv)]

        if raw_dir.exists():
            dirs = [raw_dir] + sorted(
                [
                    item
                    for item in raw_dir.iterdir()
                    if item.is_dir()
                ]
            )
        else:
            dirs = sorted(
                [
                    item
                    for item in Path(".").iterdir()
                    if item.is_dir()
                ]
            )
            dirs.insert(0, Path("."))

        selected_root = select_from_list(dirs, "Root Folder")
        root_folder = Path(selected_root)

    else:
        if args.root:
            root_folder = Path(args.root.split(",")[0].strip() or ".")
        else:
            print("Warning: root folder not given. Using current directory '.'")

    # ---------------------------
    # 3. Read Metadata
    # ---------------------------

    all_rows = []
    original_fieldnames = []

    for mf in metadata_files:
        try:
            with Path(mf).open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fields = reader.fieldnames or []

                if not original_fieldnames:
                    original_fieldnames = fields

                all_rows.extend(list(reader))

        except Exception as e:
            print(f"Error reading {mf}: {e}")
            return None

    # ---------------------------
    # 4. Header and Prefix Logic
    # ---------------------------

    has_subfolder = "Subfolder" in original_fieldnames
    has_prefix = "Prefix" in original_fieldnames
    has_date = "Date" in original_fieldnames

    fixed_prefix = "HR"

    if not has_prefix:
        user_prefix = input("Prefix column missing. Enter default prefix [Press Enter for 'HR']: ").strip()
        fixed_prefix = user_prefix if user_prefix else "HR"

    fixed_date = ""

    if not has_date:
        fixed_date = input("Date column missing. Enter fixed Date: ").strip()

    processed_count = 0
    skipped_blank = 0
    skipped_invalid_format = 0
    skipped_missing_file = 0

    curr_prefix = fixed_prefix
    curr_date = fixed_date
    curr_subfolder = ""

    spectral_headers = None
    output_data = []
    log_entries = []

    # ---------------------------
    # 5. First Pass: Find Spectral Headers
    # ---------------------------

    for row in all_rows:
        f_val = row.get("FileNum", "").strip()

        sub = row.get("Subfolder", "").strip() or curr_subfolder
        pre = row.get("Prefix", "").strip() or curr_prefix
        dt = row.get("Date", "").strip() or curr_date

        if is_valid_filenum(f_val):
            test_path = build_filepath(root_folder, sub, pre, dt, f_val)
            wv, _ = parse_sig_file(test_path)

            if wv:
                spectral_headers = wv
                break

    # ---------------------------
    # 6. Second Pass: Process All Rows
    # ---------------------------

    for idx, row in enumerate(all_rows, 1):
        f_val = row.get("FileNum", "").strip()

        if has_subfolder and row.get("Subfolder"):
            curr_subfolder = row["Subfolder"].strip()

        if has_prefix and row.get("Prefix"):
            curr_prefix = row["Prefix"].strip()

        if has_date and row.get("Date"):
            curr_date = row["Date"].strip()

        out_row = dict(row)

        if has_prefix:
            out_row["Prefix"] = curr_prefix

        if has_date:
            out_row["Date"] = curr_date

        if has_subfolder:
            out_row["Subfolder"] = curr_subfolder

        out_row["Calculated_FilePath"] = ""

        if spectral_headers:
            for h in spectral_headers:
                out_row[h] = ""

        if not f_val:
            skipped_blank += 1
            log_entries.append(f"Row {idx}: Blank FileNum found.")

        elif not is_valid_filenum(f_val):
            skipped_invalid_format += 1
            log_entries.append(f"Row {idx}: Invalid FileNum format '{f_val}'.")

        else:
            target_path = build_filepath(
                root_folder,
                curr_subfolder,
                curr_prefix,
                curr_date,
                f_val
            )

            out_row["Calculated_FilePath"] = str(make_relative_path(target_path, root_folder))

            wv, ref = parse_sig_file(target_path)

            if wv and ref:
                for h, v in zip(wv, ref):
                    out_row[h] = v

                processed_count += 1

            else:
                skipped_missing_file += 1
                log_entries.append(f"Row {idx}: File missing at {target_path}")

        output_data.append(out_row)

    # ---------------------------
    # 7. Write CSV, Log and Summary
    # ---------------------------

    final_headers = original_fieldnames + ["Calculated_FilePath"] + (spectral_headers or [])

    try:
        with output_csv.open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(output_data)

    except Exception as e:
        print(f"Error writing CSV to {output_csv}: {e}")
        return None

    with log_path.open("w", encoding="utf-8") as log_f:
        log_f.write(f"LOG REPORT - Generated: {get_log_timestamp()}\n")
        log_f.write("\nSuccess Metrics!!\n")
        log_f.write(f"Total Rows in Metadata: {len(all_rows)}\n")
        log_f.write(f"Successfully Matched Files: {processed_count}\n")
        log_f.write(f"Rows with Blank FileNum: {skipped_blank}\n")
        log_f.write(f"Rows with Invalid FileNum Format: {skipped_invalid_format}\n")
        log_f.write(f"Rows with Missing .sig Files: {skipped_missing_file}\n")
        log_f.write("=" * 50 + "\n\n")

        for entry in log_entries:
            log_f.write(f"{entry}\n")

    summary = {
        "timestamp": get_log_timestamp(),
        "total_rows": len(all_rows),
        "matched_files": processed_count,
        "blank_filenum": skipped_blank,
        "invalid_filenum": skipped_invalid_format,
        "missing_sig_files": skipped_missing_file,
        "output_directory": str(output_directory),
        "output_csv": str(output_csv),
        "heatmap_output": str(heatmap_output_path)+".png",
        "spectral_graph_output": str(spectral_graph_output_path)+".png",
        "report_markdown_output": str(report_markdown_output_path),
        "report_html_output": str(report_html_output_path),
        "report_pdf_output": str(report_pdf_output_path),
        "outlier_output": str(outlier_output_path) if args.outlier_analysis else None,
        "log_file": str(log_path),
        "summary_file": str(summary_path)
    }

    if args.output:
        summary["requested_output"] = str(output_directory)

    if custom_prefix:
        summary["custom_output_name"] = custom_prefix

    if raw_location_path is not None:
        summary["raw_location_path"] = str(raw_location_path)

    summary["dark_mode"] = args.dark_mode
    summary["outlier_analysis"] = args.outlier_analysis

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    # ---------------------------
    # Terminal Output
    # ---------------------------

    print("\nProcessing Complete!")
    print(f"Total Rows Processed: {len(all_rows)}")
    print(f"Files Found and Merged: {processed_count}")
    print(f"Warnings Logged: {len(log_entries)}")

    print("\nOutputs saved:")
    print(f"- CSV: {output_csv}")
    print(f"- Log: {log_path}")
    print(f"- JSON: {summary_path}")

    return {
        "output_csv": output_csv,
        "merged_output_name": merged_output_name,
        "heatmap_output_name": heatmap_output_path,
        "spectral_graph_output_name": spectral_graph_output_path,
        "report_output_name": report_output_name,
        "report_markdown_output": report_markdown_output_path,
        "report_html_output": report_html_output_path,
        "report_pdf_output": report_pdf_output_path,
        "outlier_output_name": outlier_output_path,
        "output_directory": output_directory,
        "raw_location_path": raw_location_path,
        "dark_mode": args.dark_mode,
        "outlier_analysis": args.outlier_analysis,
        "summary_path": summary_path,
        "log_path": log_path,
        "total_rows": len(all_rows),
        "matched_files": processed_count,
        "warnings_logged": len(log_entries),
        "script_dir": script_dir
    }

if __name__ == "__main__":
    # Backward compatibility for users who still run scripts/pipeline.py directly.
    # The preferred public entrypoint is hyperkey.py.
    try:
        from workflow import run_pipeline
        run_pipeline()
    except Exception as error:
        print(f"\nHyperkey failed: {error}")
        raise SystemExit(1)

