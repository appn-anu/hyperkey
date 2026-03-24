
# Usage: python CanolaS2S-integrate-reflectances.py data-in.csv <path to raw data folder> data-integrated.csv



# This script appends data from files to a CSV spreadsheet.
#
# Each line in the spreadsheet has a file path in the `FilePath` column, e.g.:
# ```
# X,Y,FilePath
# 1,2,Day2_1/S2S01.090425.0100.sig
# 3,4,Day2_1/S2S01.090425.0090.sig
# ```
# All other columns in the input spreadsheet are irrelevant to this script, but need to be copied over to the new spreadsheet.
#
# Following that file path within some root raw data folder goes to a `.sig` file containing the following (`[...]` denotes other data in the file - there will only be one `data=` line where the data we're looking for starts):
# ```
# [...]
# data=
# 339.1  1145.48  1165.94  101.79
# 340.5  1186.50  1206.28  101.67
# [...]
# 2512.5  54016.73  53718.02  99.45
# 2514.6  54008.25  53705.40  99.44
# ```
# The first number in each line of the "data" section of the `.sig` file denotes a wavelength, and the 4th number denotes a reflectance value at that wavelength. Use the first file scanned to create an arbitrary number of additional columns for the new spreadsheet (one column per wavelength) - all subsequent files for a given input spreadsheet will be using the same data format and thus same wavelengths.
#
# For each line of the output spreadsheet, add only the reflectance values.
#
# An example line for something with only 4 wavelengths:
# ```
# X,Y,FilePath,339.1,340.5,2512.5,2514.6
# 1,2,Day2_1/S2S01.090425.0100.sig,101.79,101.67,99.45,99.44
# ```
#
# Also, the Python script should take as command line arguments the input spreadsheet filename, root raw data folder path for the file paths, and output spreadsheet filename.



import csv
import os
import argparse
import sys

def parse_sig_file(file_path):
    """
    Parses the .sig file.
    Returns a list of wavelengths (headers) and a list of reflectance values.
    """
    wavelengths = []
    reflectance_values = []
    data_section_found = False

    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()

                # Check for the start of the data section
                if line == 'data=':
                    data_section_found = True
                    continue

                # Process data lines
                if data_section_found and line:
                    parts = line.split()
                    # Ensure the line has enough columns (at least 4)
                    if len(parts) >= 4:
                        # Column 0 is Wavelength, Column 3 is Reflectance
                        # We keep them as strings to avoid floating point formatting issues
                        wavelengths.append(parts[0])
                        reflectance_values.append(parts[3])

        return wavelengths, reflectance_values

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None, None

def main():
    parser = argparse.ArgumentParser(description="Append .sig file data to a CSV spreadsheet.")
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument("root_folder", help="Root folder path for the raw data files")
    parser.add_argument("output_csv", help="Path to the output CSV file")

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input_csv):
        print(f"Error: Input CSV '{args.input_csv}' does not exist.")
        return

    # Check if root folder exists
    if not os.path.exists(args.root_folder):
        print(f"Error: Root folder '{args.root_folder}' does not exist.")
        return

    rows_to_write = []
    new_headers = []

    # Read the input CSV
    with open(args.input_csv, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        # We need to verify 'FilePath' exists
        if 'FilePath' not in reader.fieldnames:
            print("Error: Column 'FilePath' not found in input CSV.")
            return

        # We must process the first row specifically to determine the new CSV headers
        # (Wavelengths) before we can start writing the output file.

        # Convert reader to list to handle iteration easily (assuming fits in memory)
        # If files are massive, a two-pass approach or buffering is better,
        # but for text CSVs, list conversion is usually fine.
        input_rows = list(reader)

        if not input_rows:
            print("Error: Input CSV is empty.")
            return

        print(f"Processing {len(input_rows)} rows...")

        # 1. Determine Headers from the first valid file
        first_valid_idx = -1

        for i, row in enumerate(input_rows):
            full_path = os.path.join(args.root_folder, row['FilePath'])

            if os.path.exists(full_path):
                wv, ref = parse_sig_file(full_path)
                if wv:
                    new_headers = wv
                    first_valid_idx = i
                    break

        if not new_headers:
            print("Error: Could not extract data from any .sig files referenced in the input CSV.")
            return

        # 2. Prepare Output
        output_fieldnames = reader.fieldnames + new_headers

        with open(args.output_csv, 'w', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()

            # 3. Process all rows
            for row in input_rows:
                full_path = os.path.join(args.root_folder, row['FilePath'])

                # Get the data
                # optimization: we already parsed one file above, but parsing it again
                # is negligible for simplicity.
                wv, ref = parse_sig_file(full_path)

                if wv and ref:
                    # Sanity check: ensure this file has same number of wavelengths as the header
                    if len(wv) != len(new_headers):
                        print(f"Warning: File {row['FilePath']} has {len(wv)} data points, "
                              f"expected {len(new_headers)}. Data might be misaligned.")

                    # Map reflectance values to the wavelength headers
                    # We assume strict ordering as per prompt instructions
                    for header_wv, val in zip(new_headers, ref):
                        row[header_wv] = val
                else:
                    # Handle missing file or empty data (leave columns empty)
                    pass

                writer.writerow(row)

    print(f"Successfully created '{args.output_csv}'")

if __name__ == "__main__":
    main()
