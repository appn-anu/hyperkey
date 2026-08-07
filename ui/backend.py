from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the Hyperkey project root (the parent of the ui package)."""
    return Path(__file__).resolve().parent.parent


def _import_pipeline_module():
    """
    Import scripts/pipeline.py without requiring scripts/ to be a Python package.

    Adding scripts/ to sys.path also preserves the existing follow-up imports such
    as ``from visualise_heatmap import ...`` used by the current project.
    """
    scripts_dir = project_root() / "scripts"
    if not scripts_dir.exists():
        raise RuntimeError(
            f"Hyperkey scripts directory was not found: {scripts_dir}. "
            "Place the ui folder and hyperkey.py in the project root beside scripts/."
        )

    scripts_text = str(scripts_dir)
    if scripts_text not in sys.path:
        sys.path.insert(0, scripts_text)

    return importlib.import_module("pipeline")


def _read_generated_summary(result: dict[str, Any]) -> dict[str, Any]:
    output_directory = result.get("output_directory")
    if not output_directory:
        return {}

    summary_path = Path(output_directory) / "summary.json"
    if not summary_path.exists():
        return {}

    try:
        with summary_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_generated_log(result: dict[str, Any]) -> list[str]:
    output_directory = result.get("output_directory")
    if not output_directory:
        return []

    log_path = Path(output_directory) / "error_log.txt"
    if not log_path.exists():
        return []

    try:
        return log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []


def run_hyperkey_backend(arguments: list[str]) -> dict[str, object] | None:
    """
    Run the same full pipeline used by the root-level ``hyperkey.py`` CLI.

    The next backend refactor adds ``pipeline.run_pipeline(cli_arguments=None)``.
    Keeping this single boundary ensures the Flet form, the Flet CLI fallback,
    and the public command-line entrypoint all execute the exact same workflow.
    """
    pipeline = _import_pipeline_module()
    runner = getattr(pipeline, "run_pipeline", None)

    if runner is None:
        raise RuntimeError(
            "The UI is installed, but scripts/pipeline.py still needs the Hyperkey "
            "integration refactor: add run_pipeline(cli_arguments=None) so imported "
            "runs execute extraction, visualisations, outlier analysis and report generation."
        )

    result = runner(arguments)
    if result is None:
        return None

    if not isinstance(result, dict):
        return {"result": result}

    # Prefer the generated summary metrics for the Results screen while retaining
    # every path/value returned by run_pipeline().
    combined: dict[str, object] = dict(result)
    combined.update(_read_generated_summary(result))

    log_lines = _read_generated_log(result)
    if log_lines:
        combined["_logs"] = log_lines

    return combined
