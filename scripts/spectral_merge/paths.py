from __future__ import annotations

import os
from .config import ProjectPaths
from .validators import format_filenum


def get_project_root(entry_file: str) -> tuple[str, str]:
    """
    Return script_dir and project_root.

    Compatibility rule:
    - If extractPro.py is inside a folder named scripts/, project_root is its parent.
    - Otherwise, project_root is the folder containing extractPro.py.
    """
    script_dir = os.path.dirname(os.path.abspath(entry_file))
    if os.path.basename(script_dir).lower() == "scripts":
        project_root = os.path.abspath(os.path.join(script_dir, ".."))
    else:
        project_root = script_dir
    return script_dir, project_root


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def resolve_output_csv(output_arg: str | None, default_output_dir: str) -> str:
    """Resolve the final CSV output path from an optional filename or path."""
    ensure_dir(default_output_dir)

    if not output_arg:
        return os.path.join(default_output_dir, "merged_spectral_data.csv")

    if os.path.isabs(output_arg) or os.path.dirname(output_arg):
        output_csv = output_arg
        parent = os.path.dirname(output_csv)
        if parent:
            ensure_dir(parent)
        return output_csv

    return os.path.join(default_output_dir, output_arg)


def build_project_paths(entry_file: str, output_arg: str | None) -> ProjectPaths:
    """Build all project/output paths in one place."""
    script_dir, project_root = get_project_root(entry_file)
    processed_dir = os.path.join(project_root, "data", "processed_data")
    raw_dir = os.path.join(project_root, "data", "raw_data")
    default_output_dir = os.path.join(project_root, "data", "output_data")

    output_csv = resolve_output_csv(output_arg, default_output_dir)
    log_path = os.path.join(default_output_dir, "error_log.txt")
    summary_path = os.path.join(default_output_dir, "summary.json")

    return ProjectPaths(
        script_dir=script_dir,
        project_root=project_root,
        processed_dir=processed_dir,
        raw_dir=raw_dir,
        default_output_dir=default_output_dir,
        output_csv=output_csv,
        log_path=log_path,
        summary_path=summary_path,
    )


def build_sig_filepath(
    root_folder: str,
    subfolder: str,
    prefix: str,
    date: str,
    filenum: object,
) -> str:
    """Build the expected .sig file path from metadata fields."""
    padded_filenum = format_filenum(filenum)
    filename = f"{prefix}.{date}.{padded_filenum}.sig"
    return os.path.join(root_folder, subfolder or "", filename)
