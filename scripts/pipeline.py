#!/usr/bin/env python3

# Example:
# python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -o mergedTest
# python pipeline.py "../data/processed_data/GH7-test-SubFolder.csv" -r "../data/raw_data" -o "mergedTest"
# python scripts/pipeline.py -h

import csv
import os
import json
import sys
import importlib
from datetime import datetime


# ---------------------------
# Helpers and Formatting
# ---------------------------

def get_log_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_stamp():
    return datetime.now().strftime("%d%m%Y")


def get_output_name(output_name):
    """
    Return the default output name or the custom name provided through -o/--output.
    The .csv extension is added later while generating the merged dataset.
    """
    if output_name is None:
        return f"merged_spectral_data_{get_date_stamp()}"

    cleaned_name = os.path.basename(str(output_name).strip())

    if not cleaned_name:
        raise ValueError("Output name cannot be empty.")

    return cleaned_name


def print_help():
    help_text = """
Usage:
  python scripts/pipeline.py [METADATA_CSV ...] [-r ROOT_FOLDER] [-o OUTPUT_NAME]
  python scripts/pipeline.py -h

Description:
  Extract and merge spectral data from metadata CSV files and .sig files.
  After creating the merged CSV, the pipeline runs visualizations and report generation sequentially.

Arguments:
  METADATA_CSV
      One or more metadata CSV files.
      If omitted, the CLI selection menu is shown.

Options:
  -h, --help
      Show this help message and exit.

  -r, --root ROOT_FOLDER
      Root folder containing the .sig files.
      If omitted, current directory is used.

  -o, --output OUTPUT_NAME
      Optional merged dataset name only.
      Do not include a path.
      The .csv extension is added automatically.

Examples:
  python scripts/pipeline.py -h

  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data

  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data -o mergedTest

Notes:
  - If -o/--output is not provided, the default output is:
    merged_spectral_data_DDMMYYYY.csv

  - If -o/--output is provided, the summary JSON includes:
    "custom_output_name": "your_output_name"

  - The visualization modules are called through their main() functions.
    Their sys.argv is set like this:
    visualise_heatmap.py <merged_csv_path> -n <output_name>
    visualise_measurement.py <merged_csv_path> -n <output_name>
"""
    print(help_text.strip())


def parse_pipeline_cli_args(argv):
    """
    Parse command-line arguments using sys.argv style logic.

    Supported:
      -h / --help
      -r / --root
      -o / --output

    Everything else is treated as a metadata CSV path.
    """
    metadata_files = []
    root_folder = None
    output_name = None

    i = 0

    while i < len(argv):
        arg = argv[i]

        if arg in ("-h", "--help"):
            return {
                "help": True,
                "metadata_files": [],
                "root": None,
                "output": None
            }

        elif arg in ("-r", "--root"):
            if i + 1 >= len(argv):
                raise ValueError("Root folder must be provided after -r or --root")

            root_folder = argv[i + 1]
            i += 2

        elif arg in ("-o", "--output"):
            if i + 1 >= len(argv):
                raise ValueError("Output name must be provided after -o or --output")

            output_name = argv[i + 1]
            i += 2

        elif arg.startswith("-"):
            raise ValueError(f"Unknown option: {arg}")

        else:
            metadata_files.append(arg)
            i += 1

    return {
        "help": False,
        "metadata_files": metadata_files,
        "root": root_folder,
        "output": output_name
    }


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


def build_filepath(root, subfolder, prefix, date, filenum):
    padded_f = format_filenum(filenum)
    filename = f"{prefix}.{date}.{padded_f}.sig"

    if subfolder in [".", "./"]:
        subfolder = ""

    return os.path.join(root, subfolder or "", filename)


def parse_sig_file(filepath):
    wavelengths = []
    reflectance = []
    data_section = False

    try:
        if not os.path.exists(filepath):
            return None, None

        with open(filepath, "r") as f:
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


def run_module_main(module_name, display_name, argv=None):
    """
    Import a module and call its main() function directly.

    This avoids subprocess execution.

    For modules that use sys.argv internally, this function temporarily sets sys.argv.
    Example for visualization modules:
      sys.argv = ["visualise_heatmap.py", output_csv, "-n", output_csv_name]
    """
    if argv is None:
        argv = []

    print(f"\nRunning {display_name} ...")

    old_argv = sys.argv[:]

    try:
        sys.argv = [display_name] + argv

        module = importlib.import_module(module_name)

        if not hasattr(module, "main"):
            raise AttributeError(f"{display_name} does not have a main() function.")

        module.main()

        print(f"{display_name} completed successfully.")

    except Exception as e:
        print(f"\n{display_name} failed.")
        print(f"Error: {e}")
        raise

    finally:
        sys.argv = old_argv


# ---------------------------
# Main Logic
# ---------------------------

def main():
    try:
        cli_args = parse_pipeline_cli_args(sys.argv[1:])
    except ValueError as e:
        print(f"Argument error: {e}")
        print("Use -h or --help to see usage.")
        return None

    if cli_args["help"]:
        print_help()
        return {
            "help_requested": True
        }

    # ---------------------------
    # 1. Setup Output Directory and Paths
    # ---------------------------

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))

    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    default_dir = os.path.join(project_root, "data", "output_data")
    os.makedirs(default_dir, exist_ok=True)

    try:
        output_csv_name = get_output_name(cli_args["output"])
    except ValueError as e:
        print(f"Invalid output name: {e}")
        return None

    output_csv_filename = f"{output_csv_name}.csv"
    output_csv = os.path.join(default_dir, output_csv_filename)

    log_path = os.path.join(default_dir, "error_log.txt")
    summary_path = os.path.join(default_dir, "summary.json")

    # ---------------------------
    # 2. Selection Phase
    # ---------------------------

    metadata_files = cli_args["metadata_files"]
    root_folder = "."

    processed_dir = os.path.join(project_root, "data", "processed_data")
    raw_dir = os.path.join(project_root, "data", "raw_data")

    if not metadata_files:
        search_csv_path = processed_dir if os.path.exists(processed_dir) else "."

        csv_files = [
            os.path.join(search_csv_path, f)
            for f in os.listdir(search_csv_path)
            if f.lower().endswith(".csv")
        ]

        selected_csv = select_from_list(csv_files, "Metadata CSV")

        if not selected_csv:
            return None

        metadata_files = [selected_csv]

        if os.path.exists(raw_dir):
            dirs = [raw_dir] + [
                os.path.join(raw_dir, d)
                for d in os.listdir(raw_dir)
                if os.path.isdir(os.path.join(raw_dir, d))
            ]
        else:
            dirs = [
                d for d in os.listdir(".")
                if os.path.isdir(d)
            ]
            dirs.insert(0, ".")

        root_folder = select_from_list(dirs, "Root Folder")

    else:
        if cli_args["root"]:
            root_folder = cli_args["root"].split(",")[0].strip() or "."
        else:
            print("Warning: root folder not given. Using current directory '.'")

    # ---------------------------
    # 3. Read Metadata
    # ---------------------------

    all_rows = []
    original_fieldnames = []

    for mf in metadata_files:
        try:
            with open(mf, newline="") as f:
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

            out_row["Calculated_FilePath"] = os.path.relpath(target_path, root_folder)

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
        with open(output_csv, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(output_data)

    except Exception as e:
        print(f"Error writing CSV to {output_csv}: {e}")
        return None

    with open(log_path, "w") as log_f:
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
        "output_csv": output_csv,
        "log_file": log_path
    }

    if cli_args["output"]:
        summary["custom_output_name"] = output_csv_name

    with open(summary_path, "w") as file:
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
        "help_requested": False,
        "output_csv": output_csv,
        "output_csv_name": output_csv_name,
        "script_dir": script_dir
    }


if __name__ == "__main__":
    result = main()

    if not result:
        print("\nPipeline stopped because main processing failed.")
        raise SystemExit(1)

    if result.get("help_requested"):
        raise SystemExit(0)

    output_csv = result["output_csv"]
    output_csv_name = result["output_csv_name"]

    # ---------------------------
    # Run Follow-up Modules Sequentially
    # ---------------------------

    try:
        run_module_main(
            "visualise_heatmap",
            "visualise_heatmap.py",
            argv=[output_csv, "-n", output_csv_name]
        )

        run_module_main(
            "visualise_measurement",
            "visualise_measurement.py",
            argv=[output_csv, "-n", output_csv_name]
        )

        run_module_main(
            "report",
            "report.py",
            argv=[]
        )

    except Exception:
        print("\nPipeline stopped because a follow-up module failed.")
        raise SystemExit(1)

    print("\nFULL PIPELINE COMPLETED!")