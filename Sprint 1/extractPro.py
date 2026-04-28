#!/usr/bin/env python3

import csv
import os
import sys
import argparse
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
        print(f"Invalid selection. Please enter 0 or 1-{len(items)}.")

def is_valid_filenum(val):
    if val is None: return False
    val = str(val).strip()
    return val.isdigit() and 0 <= int(val) <= 9999

def format_filenum(val):
    return str(int(val)).zfill(4)

def build_filepath(root, subfolder, prefix, date, filenum):
    filename = f"{prefix}.{date}.{filenum}.sig"
    return os.path.join(root, subfolder or "", filename)

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
    except Exception:
        return None, None

# ---------------------------
# Main Logic
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="Extract and Merge Spectral Metadata")
    parser.add_argument('metadata_files', nargs='*', help="One or more metadata CSV files")
    parser.add_argument('-c', '--config', help="Root folder, comma separated")
    args = parser.parse_args()

    # 1. Setup Output Folder
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    log_path = os.path.join(output_dir, "error_log.txt")
    with open(log_path, "w") as log_f:
        log_f.write(f"Log Created: {get_log_timestamp()}\n" + "="*30 + "\n")

    # 2. Selection Phase
    metadata_files = args.metadata_files
    root_folder = "."

    if not metadata_files:
        csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
        selected_csv = select_from_list(csv_files, "Metadata CSV")
        if not selected_csv: return
        metadata_files = [selected_csv]
        
        dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        dirs.insert(0, ".")
        root_folder = select_from_list(dirs, "Root Folder")
    else:
        if args.config:
            root_folder = args.config.split(',')[0].strip() or "."

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

    # 5. Processing
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

    for idx, row in enumerate(all_rows, 1):
        f_val = row.get("FileNum", "").strip()
        
        # Fill forward logic
        if has_subfolder and row.get("Subfolder"): curr_subfolder = row["Subfolder"].strip()
        if has_prefix and row.get("Prefix"): curr_prefix = row["Prefix"].strip()
        if has_date and row.get("Date"): curr_date = row["Date"].strip()

        # Validation
        if not f_val:
            skipped_blank += 1
            log_entries.append(f"Row {idx}: Missing FileNum.")
            continue
            
        if not is_valid_filenum(f_val):
            skipped_invalid_format += 1
            log_entries.append(f"Row {idx}: Invalid FileNum format '{f_val}'.")
            continue

        # File Existence Check
        target_path = build_filepath(root_folder, curr_subfolder, curr_prefix, curr_date, format_filenum(f_val))
        
        if not os.path.exists(target_path):
            skipped_missing_file += 1
            log_entries.append(f"Row {idx}: File not found at {target_path}")
            continue

        # Valid File Found
        wv, ref = parse_sig_file(target_path)
        if wv:
            if not spectral_headers: spectral_headers = wv
            
            out_row = dict(row)
            out_row["Calculated_FilePath"] = os.path.relpath(target_path, root_folder)
            # Update with fill-forward values for consistency
            if has_prefix: out_row["Prefix"] = curr_prefix
            if has_date: out_row["Date"] = curr_date
            if has_subfolder: out_row["Subfolder"] = curr_subfolder
            
            for h, v in zip(wv, ref):
                out_row[h] = v
            
            output_data.append(out_row)
            processed_count += 1
        else:
            log_entries.append(f"Row {idx}: Could not parse data from {target_path}")

    # 6. Write Final Output
    output_csv = os.path.join(output_dir, "merged_spectral_data.csv")
    final_headers = original_fieldnames + ["Calculated_FilePath"] + (spectral_headers or [])
    
    with open(output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(output_data)

    # 7. Finalize Log with Metrics
    with open(log_path, "a") as log_f:
        log_f.write(f"Total Rows Evaluated: {len(all_rows)}\n")
        log_f.write(f"Successfully Processed: {processed_count}\n")
        log_f.write(f"Skipped (Blank): {skipped_blank}\n")
        log_f.write(f"Skipped (Invalid Format): {skipped_invalid_format}\n")
        log_f.write(f"Skipped (File Not Found): {skipped_missing_file}\n")
        log_f.write("-" * 30 + "\n")
        for entry in log_entries:
            log_f.write(f"[{get_log_timestamp()}] {entry}\n")

    # Console Output
    print(f"\nSuccess!")
    print(f"- Total Rows: {len(all_rows)}")
    print(f"- Rows Processed: {processed_count}")
    print(f"- Rows Skipped: {skipped_blank + skipped_invalid_format + skipped_missing_file}")
    print(f"  - Blank: {skipped_blank}")
    print(f"  - Invalid Format: {skipped_invalid_format}")
    print(f"  - Missing File: {skipped_missing_file}")
    print(f"\nFiles created in '{output_dir}':")
    print(f"- CSV: {os.path.basename(output_csv)}")
    print(f"- Log: {os.path.basename(log_path)}")

if __name__ == "__main__":
    main()