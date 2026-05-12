from __future__ import annotations

import os
from .config import RunStats
from .metadata import get_default_metadata_values
from .paths import build_sig_filepath
from .sig_parser import parse_sig_file
from .validators import is_valid_filenum


def _find_spectral_headers(
    rows: list[dict[str, str]],
    root_folder: str,
    fixed_prefix: str,
    fixed_date: str,
) -> list[str] | None:
    """Find wavelengths from the first valid and readable .sig file."""
    current_subfolder = ""
    current_prefix = fixed_prefix
    current_date = fixed_date

    for row in rows:
        filenum = (row.get("FileNum") or "").strip()
        subfolder = (row.get("Subfolder") or "").strip() or current_subfolder
        prefix = (row.get("Prefix") or "").strip() or current_prefix
        date = (row.get("Date") or "").strip() or current_date

        if row.get("Subfolder"):
            current_subfolder = row["Subfolder"].strip()
        if row.get("Prefix"):
            current_prefix = row["Prefix"].strip()
        if row.get("Date"):
            current_date = row["Date"].strip()

        if is_valid_filenum(filenum):
            test_path = build_sig_filepath(root_folder, subfolder, prefix, date, filenum)
            wavelengths, _ = parse_sig_file(test_path)
            if wavelengths:
                return wavelengths

    return None


def process_metadata_rows(
    rows: list[dict[str, str]],
    original_fieldnames: list[str],
    root_folder: str,
) -> tuple[list[dict[str, str]], list[str], RunStats]:
    """Merge metadata rows with spectral values using a left-join style process."""
    has_subfolder = "Subfolder" in original_fieldnames
    has_prefix = "Prefix" in original_fieldnames
    has_date = "Date" in original_fieldnames

    fixed_prefix, fixed_date = get_default_metadata_values(original_fieldnames)
    spectral_headers = _find_spectral_headers(rows, root_folder, fixed_prefix, fixed_date)

    stats = RunStats(total_rows=len(rows))
    output_data: list[dict[str, str]] = []

    current_subfolder = ""
    current_prefix = fixed_prefix
    current_date = fixed_date

    for row_number, row in enumerate(rows, 1):
        filenum = (row.get("FileNum") or "").strip()

        if has_subfolder and row.get("Subfolder"):
            current_subfolder = row["Subfolder"].strip()
        if has_prefix and row.get("Prefix"):
            current_prefix = row["Prefix"].strip()
        if has_date and row.get("Date"):
            current_date = row["Date"].strip()

        output_row = dict(row)
        if has_prefix:
            output_row["Prefix"] = current_prefix
        if has_date:
            output_row["Date"] = current_date
        if has_subfolder:
            output_row["Subfolder"] = current_subfolder

        output_row["Calculated_FilePath"] = ""
        if spectral_headers:
            for header in spectral_headers:
                output_row[header] = ""

        if not filenum:
            stats.skipped_blank += 1
            stats.log_entries.append(f"Row {row_number}: Blank FileNum found.")
        elif not is_valid_filenum(filenum):
            stats.skipped_invalid_format += 1
            stats.log_entries.append(f"Row {row_number}: Invalid FileNum format '{filenum}'.")
        else:
            target_path = build_sig_filepath(
                root_folder,
                current_subfolder,
                current_prefix,
                current_date,
                filenum,
            )
            output_row["Calculated_FilePath"] = os.path.relpath(target_path, root_folder)

            wavelengths, reflectance = parse_sig_file(target_path)
            if wavelengths and reflectance:
                for header, value in zip(wavelengths, reflectance):
                    output_row[header] = value
                stats.processed_count += 1
            else:
                stats.skipped_missing_file += 1
                stats.log_entries.append(f"Row {row_number}: File missing at {target_path}")

        output_data.append(output_row)

    final_headers = original_fieldnames + ["Calculated_FilePath"] + (spectral_headers or [])
    return output_data, final_headers, stats
