#!/usr/bin/env python3

# Example:
# python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -o mergedTest
# python pipeline.py "../data/processed_data/GH7-test-SubFolder.csv" -r "../data/raw_data" -o "mergedTest"
# python scripts/pipeline.py -h

import csv
import os
import argparse
import json
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

    Note:
    - If the user gives -o mergedTest, output becomes mergedTest.csv
    - If the user gives -o mergedTest.csv, output becomes mergedTest.csv.csv
    """
    if output_name is None:
        return f"merged_spectral_data_{get_date_stamp()}"

    cleaned_name = os.path.basename(str(output_name).strip())

    if not cleaned_name:
        raise ValueError("Output name cannot be empty.")

    return cleaned_name


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


def run_module_main(module_name, display_name, args=None):
    """
    Import a module and call its main() function directly.

    This avoids subprocess execution and keeps the pipeline running sequentially.
    """
    if args is None:
        args = []

    print(f"\nRunning {display_name} ...")

    try:
        module = importlib.import_module(module_name)

        if not hasattr(module, "main"):
            raise AttributeError(f"{display_name} does not have a main() function.")

        module.main(*args)

        print(f"{display_name} completed successfully.")

    except Exception as e:
        print(f"\n{display_name} failed.")
        print(f"Error: {e}")
        raise


# ---------------------------
# Main Logic
# ---------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract and merge spectral data from metadata CSV files and .sig files.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/pipeline.py -h\n"
            "  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data\n"
            "  python scripts/pipeline.py data/processed_data/GH7-test-SubFolder.csv -r data/raw_data -o mergedTest\n\n"
            "Notes:\n"
            "  - If -o/--output is not provided, the default output is:\n"
            "    merged_spectral_data_DDMMYYYY.csv\n"
            "  - If -o/--output is provided, pass only the output name, not a path.\n"
            "  - The .csv extension is added automatically.\n"
        )
    )

    parser.add_argument(
        "metadata_files",
        nargs="*",
        metavar="METADATA_CSV",
        help="One or more metadata CSV files. If omitted, the CLI selection menu is shown."
    )

    parser.add_argument(
        "-r",
        "--root",
        metavar="ROOT_FOLDER",
        help="Root folder containing the .sig files. If omitted, current directory is used."
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT_NAME",
        help="Optional merged dataset name only. Do not include a path. The .csv extension is added automatically."
    )

    args = parser.parse_args()

    # ---------------------------
    # 1. Setup Output Directory and Paths
    # ---------------------------

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))

    default_dir = os.path.join(project_root, "data", "output_data")
    os.makedirs(default_dir, exist_ok=True)

    try:
        output_csv_name = get_output_name(args.output)
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

    metadata_files = args.metadata_files
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
        if args.root:
            root_folder = args.root.split(",")[0].strip() or "."
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

    if args.output:
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
        "output_csv": output_csv,
        "output_csv_name": output_csv_name,
        "script_dir": script_dir
    }


if __name__ == "__main__":
    result = main()

    if not result:
        print("\nPipeline stopped because main processing failed.")
        raise SystemExit(1)

    output_csv = result["output_csv"]
    output_csv_name = result["output_csv_name"]

    # ---------------------------
    # Run Follow-up Modules Sequentially
    # ---------------------------

    try:
        run_module_main(
            "visualise_heatmap",
            "visualise_heatmap.py",
            args=[output_csv, output_csv_name]
        )

        run_module_main(
            "visualise_measurement",
            "visualise_measurement.py",
            args=[output_csv, output_csv_name]
        )

        run_module_main(
            "report",
            "report.py",
            args=[]
        )

    except Exception:
        print("\nPipeline stopped because a follow-up module failed.")
        raise SystemExit(1)

    print("\nFULL PIPELINE COMPLETED!")