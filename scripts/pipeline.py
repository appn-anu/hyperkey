#!/usr/bin/env python3

# Example:
# python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data"
# python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -o sydneyAPPN
# python scripts/pipeline.py -h

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath


# ---------------------------
# Helpers and Formatting
# ---------------------------

def get_log_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_stamp():
    return datetime.now().strftime("%d%m%Y")


def get_custom_prefix(output_name):
    """
    Return the custom prefix provided through -o/--output.

    If -o is not given, return None.

    Example:
      -o sydneyAPPN -> sydneyAPPN
    """
    if output_name is None:
        return None

    raw_name = str(output_name).strip()

    # Remove any accidental folder path while supporting both / and \ separators.
    cleaned_name = PureWindowsPath(PurePosixPath(raw_name).name).name

    if not cleaned_name:
        raise ValueError("Output name cannot be empty.")

    return cleaned_name


def build_output_names(custom_prefix=None):
    """
    Build output names for merged dataset and visualizations.

    Default names:
      merged_spectral_data_DDMMYYYY
      heatmap_DDMMYYYY
      SpectralGraph_DDMMYYYY

    Custom names, example with -o sydneyAPPN:
      sydneyAPPN_merged_spectral_data_DDMMYYYY
      sydneyAPPN_heatmap_DDMMYYYY
      sydneyAPPN_SpectralGraph_DDMMYYYY
    """
    date_stamp = get_date_stamp()

    if custom_prefix:
        merged_output_name = f"{custom_prefix}_merged_spectral_data_{date_stamp}"
        heatmap_output_name = f"{custom_prefix}_heatmap_{date_stamp}"
        spectral_graph_output_name = f"{custom_prefix}_SpectralGraph_{date_stamp}"
    else:
        merged_output_name = f"merged_spectral_data_{date_stamp}"
        heatmap_output_name = f"heatmap_{date_stamp}"
        spectral_graph_output_name = f"SpectralGraph_{date_stamp}"

    return {
        "merged_output_name": merged_output_name,
        "heatmap_output_name": heatmap_output_name,
        "spectral_graph_output_name": spectral_graph_output_name
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
        epilog="""
Examples:
  python scripts/pipeline.py
  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data
  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data -o sydneyAPPN

Output naming:
  Without -o:
    merged_spectral_data_DDMMYYYY.csv
    heatmap_DDMMYYYY
    SpectralGraph_DDMMYYYY

  With -o sydneyAPPN:
    sydneyAPPN_merged_spectral_data_DDMMYYYY.csv
    sydneyAPPN_heatmap_DDMMYYYY
    sydneyAPPN_SpectralGraph_DDMMYYYY
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
        metavar="OUTPUT_NAME",
        help=(
            "Optional custom output prefix. Do not include a folder path or "
            "file extension."
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
    default_dir.mkdir(parents=True, exist_ok=True)

    try:
        custom_prefix = get_custom_prefix(args.output)
    except ValueError as e:
        print(f"Invalid output name: {e}")
        return None

    output_names = build_output_names(custom_prefix)

    merged_output_name = output_names["merged_output_name"]
    heatmap_output_name = output_names["heatmap_output_name"]
    spectral_graph_output_name = output_names["spectral_graph_output_name"]

    output_csv_filename = f"{merged_output_name}.csv"
    output_csv = default_dir / output_csv_filename

    log_path = default_dir / "error_log.txt"
    summary_path = default_dir / "summary.json"

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
        "output_csv": str(output_csv),
        "log_file": str(log_path)
    }

    if args.output:
        summary["custom_output_name"] = custom_prefix

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
        "heatmap_output_name": heatmap_output_name,
        "spectral_graph_output_name": spectral_graph_output_name,
        "script_dir": script_dir
    }


if __name__ == "__main__":
    result = main()

    if not result:
        print("\nPipeline stopped because main processing failed.")
        raise SystemExit(1)

    output_csv = result["output_csv"]
    heatmap_output_name = result["heatmap_output_name"]
    spectral_graph_output_name = result["spectral_graph_output_name"]

    # ---------------------------
    # Run Follow-up Modules Sequentially
    # ---------------------------

    try:
        print("\nRunning visualise_heatmap.py ...")
        from visualise_heatmap import main as heatmap_main
        heatmap_main(
            input_csv=output_csv,
            output_name=heatmap_output_name
        )
        print("visualise_heatmap.py completed successfully.")

        print("\nRunning visualise_measurement.py ...")
        from visualise_measurement import main as measurement_main
        measurement_main(
            input_csv=output_csv,
            output_name=spectral_graph_output_name
        )
        print("visualise_measurement.py completed successfully.")

        print("\nRunning report.py ...")
        from report import main as report_main
        report_main()
        print("report.py completed successfully.")

    except Exception as error:
        print("\nPipeline stopped because a follow-up module failed.")
        print(f"Error: {error}")
        raise SystemExit(1)

    print("\nFULL PIPELINE COMPLETED!")
