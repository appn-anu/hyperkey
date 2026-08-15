"""
Platform-aware paths for Hyperkey.

Hyperkey runs as a desktop app, a CLI, and an Android app built with
`flet build apk`. Those three have different ideas about where the project
lives and where it is allowed to write.

This module is the single place that answers those questions. It deliberately
does not import flet, so the pipeline in scripts/ stays usable headless and
without the UI installed.
"""

from __future__ import annotations

import os
from pathlib import Path


def is_android() -> bool:
    """
    Return True when running inside the Flet Android runtime.

    Flet sets FLET_PLATFORM in its mobile runtime. This mirrors
    flet.utils.platform_utils.is_android() without importing flet.
    Note that platform.system() reports "Linux" on Android, so it cannot
    be used for this check.
    """
    return os.getenv("FLET_PLATFORM") == "android"


def project_root() -> Path:
    """Return the Hyperkey project root (the parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def writable_data_root() -> Path:
    """
    Return the base directory for everything Hyperkey generates.

    On Android the app payload directory is read-only, so generated data goes
    to the app's private storage instead. On desktop this stays <root>/data
    so existing behaviour and documented paths are unchanged.
    """
    storage = os.getenv("FLET_APP_STORAGE_DATA")

    if is_android() and storage:
        return Path(storage)

    return project_root() / "data"


def default_output_directory() -> Path:
    """Return the default directory for merged CSVs, plots and reports."""
    return writable_data_root() / "output_data"


def configure_matplotlib() -> None:
    """
    Force headless matplotlib rendering.

    Must be called before matplotlib.pyplot is imported.

    Hyperkey always writes plots to disk, so an interactive backend is never
    wanted - and on Android there is no display server to attach to. Android
    also has no writable home directory, so matplotlib's font cache needs
    pointing at app storage or it fails to start.
    """
    os.environ.setdefault("MPLBACKEND", "Agg")

    if not is_android():
        return

    cache = os.getenv("FLET_APP_STORAGE_CACHE") or os.getenv("FLET_APP_STORAGE_TEMP")

    if cache:
        config_dir = Path(cache) / "matplotlib"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
