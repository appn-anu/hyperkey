# file: generate_filelist_csv.py
#!/usr/bin/env python3

import csv
import os
import sys

def generate_filelist_csv(metadata_csv_path, root_folder, output_csv_path):
    """
    Generates a CSV containing only a 'FilePath' column for files
    in the root folder matching the filenumbers in the metadata CSV.

    Args:
        metadata_csv_path (str): Path to the metadata CSV with 'filenumber'.
        root_folder (str): Folder containing .sig files.
        output_csv_path (str): Path to the output CSV to create.
    """
    # Validate paths
    if not os.path.exists(metadata_csv_path):
        raise FileNotFoundError(f"Metadata CSV '{metadata_csv_path}' does not exist.")
    if not os.path.exists(root_folder):
        raise FileNotFoundError(f"Root folder '{root_folder}' does not exist.")

    # Build a lookup of files in the root folder
    file_lookup = {}
    for root, _, files in os.walk(root_folder):
        for f in files:
            if f.endswith(".sig"):
                file_lookup[f] = os.path.relpath(os.path.join(root, f), root_folder)

    # Read metadata CSV
    with open(metadata_csv_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        if 'FileNum' not in reader.fieldnames:
            raise ValueError("Column 'filenumber' not found in metadata CSV.")
        metadata_rows = list(reader)

    # Prepare output rows with only 'FilePath'
    output_rows = []
    for row in metadata_rows:
        filenum = str(row['FileNum']).strip()
        matched_file = None
        for fname in file_lookup:
            if fname.endswith(filenum + ".sig"):
                matched_file = file_lookup[fname]
                break

        if matched_file:
            output_rows.append({'FilePath': matched_file})
        else:
            print(f"Warning: No file found for filenumber '{filenum}'", file=sys.stderr)

    if not output_rows:
        raise FileNotFoundError("No files found matching filenumbers in metadata.")

    # Write CSV with only 'FilePath' column
    with open(output_csv_path, 'w', newline='') as outcsv:
        writer = csv.DictWriter(outcsv, fieldnames=['FilePath'])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"File list CSV '{output_csv_path}' created with {len(output_rows)} rows.")


# CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate CSV with only 'FilePath' column from metadata.")
    parser.add_argument("metadata_csv", help="Path to the metadata CSV file")
    parser.add_argument("root_folder", help="Root folder containing .sig files")
    parser.add_argument("output_csv", help="Path to the output CSV file")
    args = parser.parse_args()

    generate_filelist_csv(args.metadata_csv, args.root_folder, args.output_csv)