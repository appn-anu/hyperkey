#!/usr/bin/env python3

# Example:
# python hyperkey.py data/example_data/example1/metadata.csv -r "data/example_data/example1"
# python hyperkey.py data/example_data/example1/metadata.csv -r "data/example_data/example1" -o data/TestHyperKey/sydneyAPPN
# python hyperkey.py data/example_data/example1/metadata.csv -r "data/example_data/example1" -l "data/raw_location/species_locations.csv"
# python hyperkey.py data/example_data/example1/metadata.csv -r "data/example_data/example1" -d
# python hyperkey.py data/example_data/example1/metadata.csv -r "data/example_data/example1" --outlier-analysis
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


def _import_workflow_module():
    """
    Import scripts/workflow.py.

    scripts/ is added to sys.path because the existing Hyperkey modules
    currently use direct imports such as:

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

    return importlib.import_module("workflow")


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

    if arguments:
        return run_cli(arguments)

    run_gui()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
