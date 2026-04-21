#!/usr/bin/env python3

import csv
import os
import argparse
import sys


# ---------------------------
# Validation
# ---------------------------
def is_valid_filenum(val):
    if val is None:
        return False
    val = str(val).strip()
    if val == "":
        return False
    if not val.isdigit():
        return False
    num = int(val)
    return 0 <= num <= 9999


def format_filenum(val):
    return str(int(val)).zfill(4)


# ---------------------------
# Build file path
# ---------------------------
def build_filepath(root, subfolder, prefix, date, filenum):
    filename = f"{prefix}.{date}.{filenum}.sig"
    return os.path.join(root, subfolder, filename)


# ---------------------------
# Parse .sig file
# ---------------------------
def parse_sig_file(filepath):
    wavelengths = []
    reflectance = []
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
    parser = argparse.ArgumentParser(description="Extract reflectance data from .sig files")

    parser.add_argument("metadata_csv")
    parser.add_argument("root_folder")
    parser.add_argument("output_csv")

    parser.add_argument("--default_prefix", default="HR")
    parser.add_argument("--default_date", required=True)

    args = parser.parse_args()

    if not os.path.exists(args.metadata_csv):
        print("Metadata CSV not found")
        return

    if not os.path.exists(args.root_folder):
        print("Root folder not found")
        return

    # Read metadata
    with open(args.metadata_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        fieldnames = reader.fieldnames

    if not rows:
        print("Empty metadata CSV")
        return

    # Detect optional columns
    has_subfolder = "Subfolder" in fieldnames
    has_prefix = "Prefix" in fieldnames
    has_date = "Date" in fieldnames

    print(f"Processing {len(rows)} rows...")

    # Step 1: Find wavelengths
    headers = None

    for row in rows:
        if not is_valid_filenum(row.get("FileNum")):
            continue

        filenum = format_filenum(row["FileNum"])

        subfolder = row.get("Subfolder", "") if has_subfolder else ""
        prefix = row.get("Prefix") if has_prefix else args.default_prefix
        date = row.get("Date") if has_date else args.default_date

        prefix = prefix.strip() if prefix else args.default_prefix
        date = date.strip() if date else args.default_date

        path = build_filepath(args.root_folder, subfolder, prefix, date, filenum)

        if os.path.exists(path):
            wv, ref = parse_sig_file(path)
            if wv:
                headers = wv
                break

    if not headers:
        print("No valid .sig files found")
        return

    # Step 2: Write output
    output_fields = ["FilePath"] + headers

    with open(args.output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=output_fields)
        writer.writeheader()

        for row in rows:
            if not is_valid_filenum(row.get("FileNum")):
                continue

            filenum = format_filenum(row["FileNum"])

            subfolder = row.get("Subfolder", "") if has_subfolder else ""
            prefix = row.get("Prefix") if has_prefix else args.default_prefix
            date = row.get("Date") if has_date else args.default_date
            

            prefix = prefix.strip() if prefix else args.default_prefix
            date = date.strip() if date else args.default_date

            path = build_filepath(args.root_folder, subfolder, prefix, date, filenum)

            out_row = {
                "FilePath": os.path.relpath(path, args.root_folder)
            }

            if os.path.exists(path):
                wv, ref = parse_sig_file(path)
                if wv and ref:
                    for h, v in zip(headers, ref):
                        out_row[h] = v
            else:
                print(f"Missing file: {path}", file=sys.stderr)

            writer.writerow(out_row)

    print(f"Created {args.output_csv}")


if __name__ == "__main__":
    main()