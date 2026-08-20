"""Temporary development launcher for the Flet UI only.

Final project integration will move the public launch/dispatch behaviour into
root-level hyperkey.py as requested.
"""

import flet as ft

from ui.app import main


if __name__ == "__main__":
    ft.run(main)
