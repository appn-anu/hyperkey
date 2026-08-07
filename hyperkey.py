#!/usr/bin/env python3
"""Public Hyperkey entrypoint.

Usage
-----
Open the Flet application:
    python hyperkey.py

Run directly from the command line:
    python hyperkey.py metadata.csv -r raw_data -o result
"""

from __future__ import annotations

import sys


def run_gui() -> None:
    import flet as ft

    from ui.app import main as flet_main

    ft.run(flet_main)


def run_cli(arguments: list[str]) -> int:
    from ui.backend import run_hyperkey_backend

    try:
        result = run_hyperkey_backend(arguments)
    except Exception as exc:
        print(f"Hyperkey failed: {exc}")
        return 1

    if result is None:
        print("Hyperkey stopped because pipeline processing failed.")
        return 1

    print("\nFULL HYPERKEY PIPELINE COMPLETED!")
    return 0


def main() -> int:
    arguments = sys.argv[1:]

    if arguments:
        return run_cli(arguments)

    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
