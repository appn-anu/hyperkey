from __future__ import annotations

import argparse
from pathlib import Path
from .metadata import choose_metadata_and_root, read_metadata_files
from .paths import build_project_paths, ensure_dir
from .processor import process_metadata_rows
from .writers import (
    print_terminal_summary,
    write_log,
    write_output_csv,
    write_summary,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(description="Extract and Merge Spectral Metadata")
    parser.add_argument("metadata_files", nargs="*", help="One or more metadata CSV files")
    parser.add_argument(
        "-r",
        "--root",
        dest="root_folder",
        help="Root folder containing .sig files. If not provided, the current directory will be used.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional full path or filename for merged CSV output",
    )
    return parser


def main() -> None:
    """Program entry point."""
    parser = build_parser()
    args = parser.parse_args()

    entry_file = str(Path(__file__).resolve().parents[1] / "extractPro.py")
    paths = build_project_paths(entry_file, args.output)
    ensure_dir(paths.default_output_dir)

    run_config = choose_metadata_and_root(args.metadata_files, args.root_folder, paths)
    if run_config is None:
        return

    try:
        rows, original_fieldnames = read_metadata_files(run_config.metadata_files)
        output_data, final_headers, stats = process_metadata_rows(
            rows=rows,
            original_fieldnames=original_fieldnames,
            root_folder=run_config.root_folder,
        )
        write_output_csv(paths.output_csv, final_headers, output_data)
        write_log(paths.log_path, stats)
        write_summary(paths.summary_path, paths.output_csv, paths.log_path, stats)
        print_terminal_summary(paths.output_csv, paths.log_path, paths.summary_path, stats)
    except Exception as exc:
        print(exc)
