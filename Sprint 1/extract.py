#!/usr/bin/env python3

import csv
import os
import argparse
import sys


def index_sig_files(root_folder):
    """
    Index all .sig files in the root folder for fast lookup.
    Returns a dict: {filename: relative_path}
    """
    file_index = {}

    for root, _, files in os.walk(root_folder):
        for f in files:
            if f.endswith(".sig"):
                rel_path = os.path.relpath(os.path.join(root, f), root_folder)
                file_index[f] = rel_path

    return file_index


def find_file_by_filenumber(file_index, filenumber):
    """
    Finds a file whose name ends with filenumber.sig
    """
    for fname, path in file_index.items():
        if fname.endswith(filenumber + ".sig"):
            return path
    return None


def parse_sig_file(file_path):
    """
    Extract wavelengths and reflectance values from a .sig file
    """
    wavelengths = []
    reflectance_values = []
    data_section = False

    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()

                if line == "data=":
                    data_section = True
                    continue

                if data_section and line:
                    parts = line.split()
                    if len(parts) >= 4:
                        wavelengths.append(parts[0])
                        reflectance_values.append(parts[3])

        return wavelengths, reflectance_values

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Extract reflectance values using metadata filenumber column"
    )
    parser.add_argument("metadata_csv", help="Metadata CSV with 'filenumber' column")
    parser.add_argument("root_folder", help="Root folder containing .sig files")
    parser.add_argument("output_csv", help="Output CSV file")

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.metadata_csv):
        print("Error: Metadata CSV not found")
        return

    if not os.path.exists(args.root_folder):
        print("Error: Root folder not found")
        return

    # Index files once (FAST)
    print("Indexing .sig files...")
    file_index = index_sig_files(args.root_folder)

    if not file_index:
        print("Error: No .sig files found in root folder")
        return

    # Read metadata
    with open(args.metadata_csv, "r", newline="") as f:
        reader = csv.DictReader(f)

        if "FileNum" not in reader.fieldnames:
            print("Error: 'filenumber' column missing")
            return

        metadata_rows = list(reader)

    if not metadata_rows:
        print("Error: Metadata CSV is empty")
        return

    print(f"Processing {len(metadata_rows)} rows...")

    # Step 1: Find first valid file to extract wavelengths
    new_headers = None

    for row in metadata_rows:
        filenum = str(row["FileNum"]).strip()
        rel_path = find_file_by_filenumber(file_index, filenum)

        if rel_path:
            full_path = os.path.join(args.root_folder, rel_path)
            wv, ref = parse_sig_file(full_path)

            if wv:
                new_headers = wv
                break

    if not new_headers:
        print("Error: Could not extract wavelengths from any file")
        return

    # Output columns
    output_fields = ["FilePath"] + new_headers

    # Step 2: Write output
    with open(args.output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=output_fields)
        writer.writeheader()

        for row in metadata_rows:
            filenum = str(row["FileNum"]).strip()
            rel_path = find_file_by_filenumber(file_index, filenum)

            output_row = {}

            if rel_path:
                full_path = os.path.join(args.root_folder, rel_path)
                wv, ref = parse_sig_file(full_path)

                output_row["FilePath"] = rel_path

                if wv and ref:
                    if len(wv) != len(new_headers):
                        print(
                            f"Warning: {rel_path} has mismatched wavelength count",
                            file=sys.stderr,
                        )

                    for h, val in zip(new_headers, ref):
                        output_row[h] = val
            else:
                print(f"Warning: No file for filenumber {filenum}", file=sys.stderr)

            writer.writerow(output_row)

    print(f"Successfully created '{args.output_csv}'")


if __name__ == "__main__":
    main()