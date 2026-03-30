#!/usr/bin/env python3

import csv
import os
import sys

# ---------------------------
# Interactive Selection Helpers
# ---------------------------
def select_from_list(items, prompt_label):
    """Displays a numbered list and returns the selected item."""
    if not items:
        print(f"No {prompt_label} found in current directory.")
        return None
    
    print(f"\n--- Select {prompt_label} ---")
    for i, item in enumerate(items, 1):
        print(f"[{i}] {item}")
    
    while True:
        choice = input(f"Enter number (1-{len(items)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        print("Invalid selection. Please try again.")

def get_files_by_ext(ext):
    return [f for f in os.listdir('.') if f.lower().endswith(ext) and os.path.isfile(f)]

def get_directories():
    return [d for d in os.listdir('.') if os.path.isdir(d)]

# ---------------------------
# Validation & Logic (Original)
# ---------------------------
def is_valid_filenum(val):
    if val is None: return False
    val = str(val).strip()
    if val == "" or not val.isdigit(): return False
    return 0 <= int(val) <= 9999

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

    # 2. Select Root Folder
    dirs = get_directories()
    # Add current directory as an option
    dirs.insert(0, ".") 
    root_folder = select_from_list(dirs, "Root Folder (where .sig files are)")
    if not root_folder: return

    # 3. Get Default Prefix & Date
    default_prefix = input("Enter default prefix [Default: HR]: ").strip() or "HR"
    default_date = ""
    while not default_date:
        default_date = input("Enter default date in the format of MMDDYY (REQUIRED, e.g., 032426): ").strip()

    # 4. Name Output File
    output_csv = input("Enter output filename [Default: processed_output.csv]: ").strip() or "processed_output.csv"

    # --- Processing Logic ---
    with open(metadata_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not rows:
        print("Empty metadata CSV")
        return

    has_subfolder = "Subfolder" in fieldnames
    has_prefix = "Prefix" in fieldnames
    has_date = "Date" in fieldnames

    print(f"\nProcessing {len(rows)} rows...")

    # Step 1: Find wavelengths for headers
    headers = None
    for row in rows:
        if not is_valid_filenum(row.get("FileNum")): continue
        
        filenum = format_filenum(row["FileNum"])
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
        print("No valid .sig files found. Check your paths and date.")
        return

    # Step 2: Write output
    output_fields = ["FilePath"] + headers
    with open(output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=output_fields)
        writer.writeheader()

        for row in rows:
            if not is_valid_filenum(row.get("FileNum")): continue

            filenum = format_filenum(row["FileNum"])
            subfolder = row.get("Subfolder", "") if has_subfolder else ""
            prefix = (row.get("Prefix") or default_prefix).strip()
            date = (row.get("Date") or default_date).strip()

            path = build_filepath(root_folder, subfolder, prefix, date, filenum)
            out_row = {"FilePath": os.path.relpath(path, root_folder)}

            if os.path.exists(path):
                wv, ref = parse_sig_file(path)
                if wv and ref:
                    for h, v in zip(headers, ref):
                        out_row[h] = v
            else:
                print(f"Missing file: {path}", file=sys.stderr)

            writer.writerow(out_row)

    print(f"\nSuccess! Created {output_csv}")

if __name__ == "__main__":
    main()