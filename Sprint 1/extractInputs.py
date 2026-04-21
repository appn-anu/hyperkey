#!/usr/bin/env python3

import csv
import os
import sys

# ---------------------------
# Interactive Selection Helpers
# ---------------------------
def select_from_list(items, prompt_label):
    """Displays a numbered list and returns the selected item or a manual entry."""
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
        
        print(f"Invalid selection. Please enter 0 to type manually or 1-{len(items)}.")

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
    if val == "" or not val.isdigit(): return False
    num = int(val)
    return 0 <= num <= 9999

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
    # 1. Select Metadata CSV
    csv_files = get_files_by_ext('.csv')
    metadata_csv = select_from_list(csv_files, "Metadata CSV")
    if not metadata_csv: return
    
    if not os.path.exists(metadata_csv):
        print(f"Error: Metadata file '{metadata_csv}' not found.")
        return

    # 2. Select Root Folder
    dirs = get_directories()
    dirs.insert(0, ".") 
    root_folder = select_from_list(dirs, "Root Folder (where .sig files are)")
    if not root_folder: return
    
    if not os.path.isdir(root_folder):
        print(f"Error: Folder '{root_folder}' not found.")
        return

    # 3. Get Default Prefix & Date
    print("\n--- Additional Configuration ---")
    default_prefix = input("Enter default prefix [Default: HR]: ").strip() or "HR"
    
    default_date = ""
    while not default_date:
        default_date = input("Enter default date in the format MMDDYY (REQUIRED, e.g., 032426): ").strip()

    # 4. Name Output File
    output_csv = input("Enter output filename [Default: processed_output.csv]: ").strip() or "processed_output.csv"

    # --- Processing Logic ---
    try:
        with open(metadata_csv, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames if reader.fieldnames else []
    except Exception as e:
        print(f"Error opening CSV: {e}")
        return

    if not rows:
        print("Empty metadata CSV or file could not be read.")
        return

    has_subfolder = "Subfolder" in fieldnames
    has_prefix = "Prefix" in fieldnames
    has_date = "Date" in fieldnames

    print(f"\nProcessing {len(rows)} rows...")

    # Step 1: Find wavelengths for headers
    headers = None
    for row in rows:
        filenum_val = row.get("FileNum")
        if not is_valid_filenum(filenum_val): continue
        
        filenum = format_filenum(filenum_val)
        subfolder = row.get("Subfolder", "") if has_subfolder else ""
        prefix = (row.get("Prefix") or default_prefix).strip()
        date = (row.get("Date") or default_date).strip()

        path = build_filepath(root_folder, subfolder, prefix, date, filenum)
        if os.path.exists(path):
            wv, _ = parse_sig_file(path)
            if wv:
                headers = wv
                break

    if not headers:
        print("No valid .sig files found. Double-check your path, prefix, and date.")
        return

    # Step 2: Write output
    output_fields = ["FilePath"] + headers
    try:
        with open(output_csv, "w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=output_fields)
            writer.writeheader()

            for row in rows:
                filenum_val = row.get("FileNum")
                if not is_valid_filenum(filenum_val): continue

                filenum = format_filenum(filenum_val)
                subfolder = row.get("Subfolder", "") if has_subfolder else ""
                prefix = (row.get("Prefix") or default_prefix).strip()
                date = (row.get("Date") or default_date).strip()

                path = build_filepath(root_folder, subfolder, prefix, date, filenum)
                
                # Use relative path for the CSV output
                try:
                    rel_path = os.path.relpath(path, root_folder)
                except ValueError:
                    rel_path = path

                out_row = {"FilePath": rel_path}

                if os.path.exists(path):
                    wv, ref = parse_sig_file(path)
                    if wv and ref:
                        for h, v in zip(headers, ref):
                            out_row[h] = v
                else:
                    print(f"Missing file: {path}", file=sys.stderr)

                writer.writerow(out_row)
        
        print(f"\nSuccess! Created '{output_csv}' with {len(headers)} spectral bands.")

    except PermissionError:
        print(f"Error: Could not write to {output_csv}. Is it open in Excel?")

if __name__ == "__main__":
    main()