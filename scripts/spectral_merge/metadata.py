from __future__ import annotations

import csv
import os
from .config import ProjectPaths, RunConfig
from .prompts import select_from_list


def choose_metadata_and_root(
    metadata_files: list[str],
    root_arg: str | None,
    paths: ProjectPaths,
) -> RunConfig | None:
    """Resolve metadata files and root folder from args or interactive prompts."""
    root_folder = "."

    if metadata_files:
        if root_arg:
            # Keep compatibility with older '-r/--config' values that may contain commas.
            root_folder = root_arg.split(",")[0].strip() or "."
        return RunConfig(metadata_files=metadata_files, root_folder=root_folder)

    search_csv_path = paths.processed_dir if os.path.exists(paths.processed_dir) else "."
    csv_files = [
        os.path.join(search_csv_path, filename)
        for filename in os.listdir(search_csv_path)
        if filename.lower().endswith(".csv")
    ]

    selected_csv = select_from_list(csv_files, "Metadata CSV")
    if not selected_csv:
        return None

    if os.path.exists(paths.raw_dir):
        root_options = [paths.raw_dir] + [
            os.path.join(paths.raw_dir, dirname)
            for dirname in os.listdir(paths.raw_dir)
            if os.path.isdir(os.path.join(paths.raw_dir, dirname))
        ]
    else:
        root_options = [
            dirname for dirname in os.listdir(".") if os.path.isdir(dirname)
        ]
        root_options.insert(0, ".")

    root_folder = select_from_list(root_options, "Root Folder")
    return RunConfig(metadata_files=[selected_csv], root_folder=root_folder)


def read_metadata_files(metadata_files: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Read one or more metadata CSV files into rows and preserve first file headers."""
    all_rows: list[dict[str, str]] = []
    original_fieldnames: list[str] = []

    for metadata_file in metadata_files:
        try:
            with open(metadata_file, newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                fields = reader.fieldnames or []
                if not original_fieldnames:
                    original_fieldnames = fields
                all_rows.extend(list(reader))
        except Exception as exc:
            raise RuntimeError(f"Error reading {metadata_file}: {exc}") from exc

    return all_rows, original_fieldnames


def get_default_metadata_values(original_fieldnames: list[str]) -> tuple[str, str]:
    """Prompt only for missing Prefix/Date columns, preserving original behaviour."""
    fixed_prefix = "HR"
    fixed_date = ""

    if "Prefix" not in original_fieldnames:
        user_prefix = input("Prefix column missing. Enter default prefix [Press Enter for 'HR']: ").strip()
        fixed_prefix = user_prefix if user_prefix else "HR"

    if "Date" not in original_fieldnames:
        fixed_date = input("Date column missing. Enter fixed Date: ").strip()

    return fixed_prefix, fixed_date
