from __future__ import annotations

import csv
import json
from .config import RunStats, get_log_timestamp


def write_output_csv(
    output_csv: str,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    """Write merged metadata and spectral data to CSV."""
    with open(output_csv, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_log(log_path: str, stats: RunStats) -> None:
    """Write text log with counters and row-level warnings."""
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"LOG REPORT - Generated: {get_log_timestamp()}\n")
        log_file.write("\nSuccess Metrics!!\n")
        log_file.write(f"Total Rows in Metadata: {stats.total_rows}\n")
        log_file.write(f"Successfully Matched Files: {stats.processed_count}\n")
        log_file.write(f"Rows with Blank FileNum: {stats.skipped_blank}\n")
        log_file.write(f"Rows with Invalid FileNum Format: {stats.skipped_invalid_format}\n")
        log_file.write(f"Rows with Missing .sig Files: {stats.skipped_missing_file}\n")
        log_file.write("=" * 50 + "\n\n")

        for entry in stats.log_entries:
            log_file.write(f"{entry}\n")


def write_summary(summary_path: str, output_csv: str, log_path: str, stats: RunStats) -> None:
    """Write machine-readable summary JSON."""
    summary = {
        "timestamp": get_log_timestamp(),
        "total_rows": stats.total_rows,
        "matched_files": stats.processed_count,
        "blank_filenum": stats.skipped_blank,
        "invalid_filenum": stats.skipped_invalid_format,
        "missing_sig_files": stats.skipped_missing_file,
        "output_csv": output_csv,
        "log_file": log_path,
    }

    with open(summary_path, "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, indent=4)


def print_terminal_summary(output_csv: str, log_path: str, summary_path: str, stats: RunStats) -> None:
    """Print final run summary to terminal."""
    print("\nProcessing Complete!")
    print(f"Total Rows Processed: {stats.total_rows}")
    print(f"Files Found & Merged: {stats.processed_count}")
    print(f"Warnings Logged: {stats.warnings_count}")
    print("\nOutputs saved:")
    print(f"- CSV: {output_csv}")
    print(f"- Log: {log_path}")
    print(f"- JSON: {summary_path}")
