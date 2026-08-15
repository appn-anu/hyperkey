#!/usr/bin/env python3

# Example:
# python hyperkey.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data"
# python hyperkey.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -o sydneyAPPN
# python hyperkey.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -l "data/raw_location/species_locations.csv"
# python hyperkey.py data/processed_data/GH7-test-SubFolder.csv -r "data/raw_data" -d
# python hyperkey.py -h

"""
Public Hyperkey entrypoint.

Usage
-----

Open the Flet application:

    python hyperkey.py


Run directly from the command line:

    python hyperkey.py metadata.csv -r raw_data


With output name:

    python hyperkey.py metadata.csv -r raw_data -o sydneyAPPN


With location data:

    python hyperkey.py metadata.csv \
        -r raw_data \
        -l species_locations.csv


With outlier analysis:

    python hyperkey.py metadata.csv \
        -r raw_data \
        --outlier-analysis
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def project_root() -> Path:
    """Return the Hyperkey project root."""
    return Path(__file__).resolve().parent


def _ensure_scripts_on_path() -> None:
    """
    Add scripts/ to sys.path.

    The existing Hyperkey modules use direct imports such as:

        from visualise_heatmap import main
        from pipeline import main

    This keeps those modules working without requiring scripts/
    to become a Python package.
    """
    scripts_dir = project_root() / "scripts"

    if not scripts_dir.exists():
        raise RuntimeError(
            f"Hyperkey scripts directory was not found: {scripts_dir}"
        )

    scripts_text = str(scripts_dir)

    if scripts_text not in sys.path:
        sys.path.insert(0, scripts_text)


def _import_workflow_module():
    """Import scripts/workflow.py."""
    _ensure_scripts_on_path()

    return importlib.import_module("workflow")


def _is_android() -> bool:
    """Return True when running inside the Flet Android runtime."""
    try:
        _ensure_scripts_on_path()

        return importlib.import_module("app_paths").is_android()
    except Exception:
        return False


def run_gui() -> None:
    """Launch the shared Flet desktop/Android interface."""
    import flet as ft

    from ui.app import main as flet_main

    ft.run(flet_main)


def run_cli(arguments: list[str]) -> int:
    """
    Run Hyperkey directly from command-line arguments.

    CLI execution intentionally calls workflow.py directly rather than
    passing through the Flet UI backend.
    """
    try:
        workflow = _import_workflow_module()

        runner = getattr(workflow, "run_pipeline", None)

        if runner is None:
            raise RuntimeError(
                "scripts/workflow.py does not provide "
                "run_pipeline(cli_arguments=None)."
            )

        result = runner(arguments)

    except Exception as exc:
        print(f"\nHyperkey failed: {exc}")
        return 1

    if result is None:
        print(
            "\nHyperkey stopped because pipeline processing failed."
        )
        return 1

    return 0


def main() -> int:
    """
    Select GUI or CLI mode.

    No arguments:
        Launch Flet.

    One or more arguments:
        Run the Hyperkey CLI workflow.
    """
    arguments = sys.argv[1:]

    # There is no command line on Android, and the runtime may pass arguments
    # of its own, so always launch the interface there.
    if arguments and not _is_android():
        return run_cli(arguments)

    run_gui()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

elif _is_android():
    # Flet's Android runtime may import the entry module rather than execute it
    # as __main__, in which case the block above never runs. Starting here
    # covers that; on desktop this branch is inert, so `import hyperkey` from
    # a test or another tool still has no side effects.
    run_gui()
