#!/usr/bin/env python3

import csv
import os
import sys
import argparse

# ---------------------------
# Interactive Selection Helpers
# ---------------------------
def select_from_list(items, prompt_label):
    print(f"\n--- Select {prompt_label} ---")
    print("[0] ENTER MANUALLY / TYPE PATH")
    
    for i, item in enumerate(items, 1):
        print(f"[{i}] {item}")
    
    while True:
        choice = input(f"Enter number (0-{len(items)}): ").strip()
        if choice == "0":
            manual_val = input(f"Type the manual value for {prompt_label}: ").strip()
            if manual_val: return manual_val
            print("Input cannot be empty.")
            continue
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        print(f"Invalid selection. Please enter 0 or 1-{len(items)}.")

def get_files_by_ext(ext):
    return [f for f in os.listdir('.') if f.lower().endswith(ext) and os.path.isfile(f)]

def get_directories():
    return [d for d in os.listdir('.') if os.path.isdir(d)]

# ---------------------------
# Validation & Logic
# ---------------------------
def is_valid_filenum(val):
    if val is None: return False
    val = str(val).strip()
    return val.isdigit() and 0 <= int(val) <= 9999

def format_filenum(val):
    return str(int(val)).zfill(4)

def build_filepath(root, subfolder, prefix, date, filenum):
    filename = f"{prefix}.{date}.{filenum}.sig"
    if subfolder:
        return os.path.join(root, subfolder, filename)
    return os.path.join(root, filename)

def parse_sig_file(filepath):
    wavelengths, reflectance = [], []
    data_section = False
    try:
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
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return None, None

# ---------------------------
# Main Logic
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract and Merge Spectral Metadata")
    parser.add_argument('metadata_files', nargs='*', help="One or more metadata CSV files")
    parser.add_argument('-c', '--config', help="Output file and root folder, comma separated (e.g., output.csv,root_dir)")
    
    args = parser.parse_args()

    # 1. Selection Phase (Args vs Interactive)
    metadata_files = args.metadata_files
    output_csv = "merged_spectral_data.csv"
    root_folder = "."

    if not metadata_files:
        # INTERACTIVE MODE
        csv_files = get_files_by_ext('.csv')
        selected_csv = select_from_list(csv_files, "Metadata CSV")
        if not selected_csv or not os.path.exists(selected_csv): return
        metadata_files = [selected_csv]

        dirs = get_directories()
        dirs.insert(0, ".") 
        selected_root = select_from_list(dirs, "Root Folder (where .sig files are)")
        if not selected_root or not os.path.isdir(selected_root): return
        root_folder = selected_root

        print("\n--- Additional Configuration ---")
        output_csv = input("Enter output filename [Default: merged_spectral_data.csv]: ").strip() or "merged_spectral_data.csv"
    else:
        # CLI ARGS MODE
        if args.config:
            parts = args.config.split(',')
            output_csv = parts[0].strip() if parts[0].strip() else "merged_spectral_data.csv"
            if len(parts) > 1 and parts[1].strip():
                root_folder = parts[1].strip()
            else:
                print("WARNING: Root folder path isn't given in config. Using current working directory.")
        else:
            print("WARNING: Root folder path isn't given. Using current working directory.")

    print("\nProcessing...")
    print(f"Metadata Files: {', '.join(metadata_files)}")
    print(f"Root Folder: {root_folder}")    
    print(f"Output CSV: {output_csv}")

    # 2. Read and Merge Metadata
    rows = []
    original_fieldnames = []

    if len(metadata_files) == 1:
        try:
            with open(metadata_files[0], newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                original_fieldnames = reader.fieldnames if reader.fieldnames else []
        except Exception as e:
            print(f"Error opening CSV: {e}")
            return
    else:
        # Merge multiple CSVs based on common headers
        header_sets = []
        all_temp_rows = []
        for mf in metadata_files:
            try:
                with open(mf, newline="") as f:
                    reader = csv.DictReader(f)
                    fields = reader.fieldnames if reader.fieldnames else []
                    header_sets.append(set(fields))
                    all_temp_rows.extend(list(reader))
            except Exception as e:
                print(f"Error opening {mf}: {e}")
                return
        if header_sets:
            common_headers = list(set.intersection(*header_sets))
            original_fieldnames = common_headers
            for r in all_temp_rows:
                rows.append({k: r.get(k, "") for k in common_headers})

    if not rows:
        print("Empty metadata CSV(s).")
        return

    # Check Headers
    has_subfolder = "Subfolder" in original_fieldnames
    has_prefix = "Prefix" in original_fieldnames
    has_date = "Date" in original_fieldnames

    fixed_prefix = None
    fixed_date = None

    if not has_prefix:
        print("WARNING: Prefix column header missing. Using default prefix 'HR'.")
        fixed_prefix = "HR"
    
    if not has_date:
        fixed_date = input("WARNING: Date column header missing. Please enter a fixed Date for entire data: ").strip()

    if not has_subfolder:
        print("WARNING: Subfolder column missing. Using the root folder to search.")

    # Fill-forward state variables
    curr_prefix = "HR"
    curr_date = ""
    curr_subfolder = ""

    # 3. First Pass - Fill forward logic, Validation, and find Spectral Headers
    spectral_headers = None
    processed_rows_data = []

    for idx, row in enumerate(rows):
        f_val = row.get("FileNum")
        if not is_valid_filenum(f_val): 
            # Still record it for accurate skipped counting later
            processed_rows_data.append((row, None, None, None, f_val))
            continue

        # --- Subfolder Logic ---
        if not has_subfolder:
            row_subfolder = ""
        else:
            val = row.get("Subfolder", "").strip()
            if idx == 0 and not val:
                print("WARNING: Subfolder first row is blank. Using root folder to search.")
                curr_subfolder = ""
            elif val:
                if "." in val or "./" in val:
                    print(f"WARNING: Subfolder '{val}' contains '.' or './' indicating root/current dir.")
                
                check_path = os.path.join(root_folder, val)
                if not os.path.isdir(check_path) and val not in [".", "./"]:
                    print(f"WARNING: Subfolder '{val}' does not exist. File will be skipped if not in root.")
                curr_subfolder = val
            row_subfolder = curr_subfolder

        # --- Prefix Logic ---
        if not has_prefix:
            row_prefix = fixed_prefix
        else:
            val = row.get("Prefix", "").strip()
            if idx == 0 and not val:
                print("WARNING: Prefix first row is missing. Using default 'HR'.")
                curr_prefix = "HR"
            elif val:
                curr_prefix = val
            row_prefix = curr_prefix

        # --- Date Logic ---
        if not has_date:
            row_date = fixed_date
        else:
            val = row.get("Date", "").strip()
            if idx == 0 and not val:
                curr_date = input("WARNING: Date is missing on the first row. Enter date: ").strip()
            elif val:
                curr_date = val
            row_date = curr_date

        processed_rows_data.append((row, row_prefix, row_date, row_subfolder, f_val))

        # Scan for headers if we haven't found them yet
        if not spectral_headers:
            test_path = build_filepath(root_folder, row_subfolder, row_prefix, row_date, format_filenum(f_val))
            if os.path.exists(test_path):
                wv, _ = parse_sig_file(test_path)
                if wv:
                    spectral_headers = wv

    if not spectral_headers:
        print("Could not find any valid .sig files to determine wavelengths.")
        return

    # 4. Write Output
    output_fields = original_fieldnames + ["Calculated_FilePath"] + spectral_headers
    processed_count = 0
    skipped_count = 0

    try:
        with open(output_csv, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=output_fields)
            writer.writeheader()

            for row_dict, prefix, date, subfolder, f_val in processed_rows_data:
                if not is_valid_filenum(f_val):
                    skipped_count += 1
                    continue

                out_row = dict(row_dict)
                path = build_filepath(root_folder, subfolder, prefix, date, format_filenum(f_val))
                
                try:
                    out_row["Calculated_FilePath"] = os.path.relpath(path, root_folder)
                except ValueError:
                     raise FileNotFoundError(f"Metadata FileNum {f_val} has no matching .sig file.\n Expected path: {path}\n")

                if os.path.exists(path):
                    wv, ref = parse_sig_file(path)
                    if wv and ref:
                        for h, v in zip(spectral_headers, ref):
                            out_row[h] = v
                else:
                    print(f"Missing file: {path}", file=sys.stderr)

                # Overwrite original values with the filled-forward ones to keep the output accurate
                if has_prefix: out_row["Prefix"] = prefix
                if has_date: out_row["Date"] = date
                if has_subfolder: out_row["Subfolder"] = subfolder

                writer.writerow(out_row)
                processed_count += 1
        
        print(f"\nSuccess!")
        print(f"- Rows Processed: {processed_count}")
        print(f"- Rows Skipped (blank/invalid FileNum): {skipped_count}")
        print(f"- Output File created: '{output_csv}'\n  (Path: {os.path.abspath(output_csv)})\n")

    except PermissionError:
        print(f"Error: {output_csv} is open in another program.")

if __name__ == "__main__":
    main()