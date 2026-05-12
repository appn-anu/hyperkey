#!/usr/bin/env python3
# python scripts/extractPro.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -o mergedTest.csv "

import csv
import os
import argparse
import json
from datetime import datetime

# ---------------------------
# Helpers & Formatting
# ---------------------------
def get_log_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        print(f"Invalid selection. Please enter 0 or 1-{len(items)}. (Press Ctrl+C to exit)")

def is_valid_filenum(val):
    if val is None: return False
    val = str(val).strip()
    return val.isdigit() and 0 <= int(val) <= 9999

def format_filenum(val):
    try:
        return str(int(val)).zfill(4)
    except:
        return val

def build_filepath(root, subfolder, prefix, date, filenum):
    padded_f = format_filenum(filenum)
    filename = f"{prefix}.{date}.{padded_f}.sig"
    return os.path.join(root, subfolder or "", filename)

def parse_sig_file(filepath):
    wavelengths, reflectance = [], []
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

# ---------------------------
# Main Logic
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract and Merge Spectral Metadata")
    parser.add_argument('metadata_files', nargs='*', help="One or more metadata CSV files")
    parser.add_argument('-r', '--root', help="Root folder")
    parser.add_argument('-o', '--output', help="Optional: Full path or filename for merged CSV output")
    args = parser.parse_args()

    # 1. Setup Output Directory and Paths
    # Get the directory where the script is actually located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Anchor to the project root (assuming script is in 'scripts/' and data is in 'data/')
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    
    # Define the default output directory relative to the project root
    default_dir = os.path.join(project_root, "data", "output_data")
    if not os.path.exists(default_dir):
        os.makedirs(default_dir)

    # Determine CSV output path logic
    if args.output:
        if os.path.isabs(args.output) or os.path.dirname(args.output):
            # It's a path (relative or absolute)
            output_csv = args.output
            # Ensure the directory for the custom path exists
            out_parent = os.path.dirname(output_csv)
            if out_parent and not os.path.exists(out_parent):
                os.makedirs(out_parent)
        else:
            # It's just a filename
            output_csv = os.path.join(default_dir, args.output)
    else:
        output_csv = os.path.join(default_dir, "merged_spectral_data.csv")

    log_path = os.path.join(default_dir, "error_log.txt")
    
    # 2. Selection Phase
    metadata_files = args.metadata_files
    root_folder = "."

    # --- CHANGES START HERE ---
    processed_dir = os.path.join(project_root, "data", "processed_data")
    raw_dir = os.path.join(project_root, "data", "raw_data")

    if not metadata_files:
        # Determine where to search for CSVs
        search_csv_path = processed_dir if os.path.exists(processed_dir) else "."
        csv_files = [os.path.join(search_csv_path, f) for f in os.listdir(search_csv_path) if f.lower().endswith('.csv')]
        
        selected_csv = select_from_list(csv_files, "Metadata CSV")
        if not selected_csv: return
        metadata_files = [selected_csv]
        
        # Determine where to search for Root Folders
        if os.path.exists(raw_dir):
            dirs = [raw_dir] + [os.path.join(raw_dir, d) for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d))]
        else:
            dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
            dirs.insert(0, ".")
            
        root_folder = select_from_list(dirs, "Root Folder")
    else:
        if args.root:
            root_folder = args.root.split(',')[0].strip() or "."
    # --- CHANGES END HERE ---

    # 3. Read Metadata
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
            return

    # 4. Header & Prefix Logic
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

    # 5. Processing Loop
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

    # First pass: find spectral headers
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

    # Second pass: Process all rows (Left Join style)
    for idx, row in enumerate(all_rows, 1):
        f_val = row.get("FileNum", "").strip()
        
        if has_subfolder and row.get("Subfolder"): curr_subfolder = row["Subfolder"].strip()
        if has_prefix and row.get("Prefix"): curr_prefix = row["Prefix"].strip()
        if has_date and row.get("Date"): curr_date = row["Date"].strip()

        out_row = dict(row)
        if has_prefix: out_row["Prefix"] = curr_prefix
        if has_date: out_row["Date"] = curr_date
        if has_subfolder: out_row["Subfolder"] = curr_subfolder
        
        out_row["Calculated_FilePath"] = ""
        if spectral_headers:
            for h in spectral_headers: out_row[h] = ""

        if not f_val:
            skipped_blank += 1
            log_entries.append(f"Row {idx}: Blank FileNum found.")
        elif not is_valid_filenum(f_val):
            skipped_invalid_format += 1
            log_entries.append(f"Row {idx}: Invalid FileNum format '{f_val}'.")
        else:
            target_path = build_filepath(root_folder, curr_subfolder, curr_prefix, curr_date, f_val)
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

    # 6. Writing Files
    final_headers = original_fieldnames + ["Calculated_FilePath"] + (spectral_headers or [])
    
    try:
        with open(output_csv, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(output_data)
    except Exception as e:
        print(f"Error writing CSV to {output_csv}: {e}")

    with open(log_path, "w") as log_f:
        log_f.write(f"LOG REPORT - Generated: {get_log_timestamp()}\n")
        log_f.write(f"\nSuccess Metrics!!\n")
        log_f.write(f"Total Rows in Metadata: {len(all_rows)}\n")
        log_f.write(f"Successfully Matched Files: {processed_count}\n")
        log_f.write(f"Rows with Blank FileNum: {skipped_blank}\n")
        log_f.write(f"Rows with Invalid FileNum Format: {skipped_invalid_format}\n")
        log_f.write(f"Rows with Missing .sig Files: {skipped_missing_file}\n")
        log_f.write("="*50 + "\n\n")
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

    summary_path = os.path.join(default_dir, "summary.json")
    with open(summary_path, "w") as file:
        json.dump(summary, file, indent=4)
    


    # Terminal Output
    print(f"\nProcessing Complete!")
    print(f"Total Rows Processed: {len(all_rows)}")
    print(f"Files Found & Merged: {processed_count}")
    print(f"Warnings Logged: {len(log_entries)}")
    print(f"\nOutputs saved:")
    print(f"- CSV: {output_csv}")
    print(f"- Log: {log_path}")
    print(f"- JSON: {summary_path}")

if __name__ == "__main__":
    main()