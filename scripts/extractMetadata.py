#!/usr/bin/env python3

import csv
import os
import sys

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
    # Returns True only if it's not empty and consists of digits
    return val.isdigit() and 0 <= int(val) <= 9999

def format_filenum(val):
    return str(int(val)).zfill(4)

def build_filepath(root, subfolder, prefix, date, filenum):
    filename = f"{prefix}.{date}.{filenum}.sig"
    return os.path.join(root, subfolder, filename)

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
# Main
# ---------------------------
def main():
    # 1. Selection Phase
    csv_files = get_files_by_ext('.csv')
    metadata_csv = select_from_list(csv_files, "Metadata CSV")
    if not metadata_csv or not os.path.exists(metadata_csv): return

    dirs = get_directories()
    dirs.insert(0, ".") 
    root_folder = select_from_list(dirs, "Root Folder (where .sig files are)")
    if not root_folder or not os.path.isdir(root_folder): return

    print("\n--- Additional Configuration ---")
    default_prefix = input("Enter default prefix [Default: HR]: ").strip() or "HR"
    default_date = ""
    while not default_date:
        default_date = input("Enter default date MMDDYY (e.g., 032426): ").strip()

    output_csv = input("Enter output filename [Default: merged_spectral_data.csv]: ").strip() or "merged_spectral_data.csv"

    print("\nProcessing...")
    print(f"Metadata CSV: {metadata_csv}")
    print(f"Root Folder: {root_folder}")    
    print(f"Default Prefix: {default_prefix}")
    print(f"Default Date: {default_date}")  
    print(f"Output CSV: {output_csv}")

    # 2. Read Metadata
    try:
        with open(metadata_csv, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            original_fieldnames = reader.fieldnames if reader.fieldnames else []
    except Exception as e:
        print(f"Error opening CSV: {e}")
        return

    if not rows:
        print("Empty metadata CSV.")
        return

    has_subfolder = "Subfolder" in original_fieldnames
    has_prefix = "Prefix" in original_fieldnames
    has_date = "Date" in original_fieldnames

    # 3. Find Spectral Headers (Wavelengths)
    print(f"\nScanning for .sig file structure...")
    spectral_headers = None
    for row in rows:
        f_val = row.get("FileNum")
        if not is_valid_filenum(f_val): continue
        
        path = build_filepath(
            root_folder, 
            row.get("Subfolder", "") if has_subfolder else "",
            (row.get("Prefix") or default_prefix).strip(),
            (row.get("Date") or default_date).strip(),
            format_filenum(f_val)
        )
        if os.path.exists(path):
            wv, _ = parse_sig_file(path)
            if wv:
                spectral_headers = wv
                break

    if not spectral_headers:
        print("Could not find any valid .sig files to determine wavelengths.")
        return

    # 4. Merge and Write Output
    output_fields = original_fieldnames + ["Calculated_FilePath"] + spectral_headers

    try:
        with open(output_csv, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=output_fields)
            writer.writeheader()

            processed_count = 0
            skipped_count = 0

            for row in rows:
                f_val = row.get("FileNum")
                
                # --- SKIP LOGIC ---
                # If FileNum is blank or non-numeric, skip the row entirely
                if not is_valid_filenum(f_val):
                    skipped_count += 1
                    continue

                out_row = dict(row)
                prefix = (row.get("Prefix") or default_prefix).strip()
                date = (row.get("Date") or default_date).strip()
                subfolder = row.get("Subfolder", "") if has_subfolder else ""
                
                path = build_filepath(root_folder, subfolder, prefix, date, format_filenum(f_val))
                
                try:
                    out_row["Calculated_FilePath"] = os.path.relpath(path, root_folder)
                except ValueError:
                     raise FileNotFoundError(f"Metadata FileNum {f_val} has no matching .sig file.\n"
                       f"Expected path: {path}"
                    )

                if os.path.exists(path):
                    wv, ref = parse_sig_file(path)
                    if wv and ref:
                        for h, v in zip(spectral_headers, ref):
                            out_row[h] = v
                else:
                    print(f"Missing file: {path}", file=sys.stderr)

                writer.writerow(out_row)
                processed_count += 1
        
        print(f"\nSuccess!")
        print(f"- Rows Processed: {processed_count}")
        print(f"- Rows Skipped (blank/invalid FileNum): {skipped_count}")
        print(f"- File created: '{output_csv}'")

    except PermissionError:
        print(f"Error: {output_csv} is open in another program.")

if __name__ == "__main__":
    main()