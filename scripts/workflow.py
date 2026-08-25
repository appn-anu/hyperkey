#!/usr/bin/env python3

"""
Hyperkey workflow orchestration.

This module runs the complete processing workflow after the extraction/merge
stage provided by pipeline.py.

It is shared by:
- hyperkey.py CLI execution
- the Flet desktop UI
- the Flet Android UI
"""

import json
from pathlib import Path

from pipeline import main as pipeline_main


# Optional developer-level overrides.
#
# Leave this empty to use the defaults defined in outlier_analysis.py.
# A developer can manually override one or more settings here without adding
# any new CLI arguments, for example:
#
# WORKFLOW_OUTLIER_OVERRIDES = {
#     "sd_threshold": 2.5,
#     "max_outliers": 30,
#     "group_by": "Name",
# }
#
# UI values, when supplied, override both these workflow overrides and the
# defaults in outlier_analysis.py for that individual run.
WORKFLOW_OUTLIER_OVERRIDES: dict[str, object] = {}


def _resolve_outlier_settings(
    ui_settings: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Resolve effective outlier settings.

    Priority, highest to lowest:
      1. Values supplied by the Flet UI for this run
      2. WORKFLOW_OUTLIER_OVERRIDES in this file
      3. Defaults defined in outlier_analysis.py
    """
    from outlier_analysis import (
        DEFAULT_DDOF,
        DEFAULT_GROUP_BY,
        DEFAULT_ID_COLUMN,
        DEFAULT_MAX_OUTLIERS,
        DEFAULT_MIN_VALID_VALUES,
        DEFAULT_SD_THRESHOLD,
    )

    settings: dict[str, object] = {
        "sd_threshold": DEFAULT_SD_THRESHOLD,
        "max_outliers": DEFAULT_MAX_OUTLIERS,
        "id_column": DEFAULT_ID_COLUMN,
        "group_by": DEFAULT_GROUP_BY,
        "min_valid_values": DEFAULT_MIN_VALID_VALUES,
        "ddof": DEFAULT_DDOF,
    }

    settings.update(WORKFLOW_OUTLIER_OVERRIDES)

    if ui_settings:
        settings.update(ui_settings)

    return settings


def run_pipeline(
    cli_arguments=None,
    outlier_settings: dict[str, object] | None = None,
):
    """
    Run the complete Hyperkey workflow.

    cli_arguments:
        Existing Hyperkey CLI-style argument list.

    outlier_settings:
        Optional UI-only outlier overrides. These values do not form part of
        Hyperkey's CLI. A normal CLI run passes None and therefore uses the
        stored workflow/outlier defaults.
    """
    result = pipeline_main(cli_arguments)

    if not result:
        raise RuntimeError("Main extraction and merge processing failed.")

    output_csv = result["output_csv"]
    heatmap_output_name = result["heatmap_output_name"]
    spectral_graph_output_name = result["spectral_graph_output_name"]
    outlier_output_name = result["outlier_output_name"]
    output_directory = result["output_directory"]
    raw_location_path = result["raw_location_path"]
    dark_mode = result["dark_mode"]
    outlier_analysis = result["outlier_analysis"]
    summary_path = result["summary_path"]

    completed_stages = ["extract_merge"]
    effective_outlier_settings: dict[str, object] | None = None

    try:
        # ---------------------------
        # 1. Heatmap
        # ---------------------------
        print("\nRunning visualise_heatmap.py ...")
        from visualise_heatmap import main as heatmap_main

        heatmap_arguments = {
            "input_path": output_csv,
            "output_name": heatmap_output_name,
            "dark_mode": dark_mode
        }

        if raw_location_path is not None:
            heatmap_arguments["raw_location_path"] = raw_location_path

        heatmap_main(**heatmap_arguments)
        completed_stages.append("heatmap")
        print("visualise_heatmap.py completed successfully.")

        # ---------------------------
        # 2. Spectral Measurement Graph
        # ---------------------------
        print("\nRunning visualise_measurement.py ...")
        from visualise_measurement import main as measurement_main
        measurement_main(
            input_path=output_csv,
            output_name=spectral_graph_output_name,
            dark_mode=dark_mode
        )
        completed_stages.append("spectral_graph")
        print("visualise_measurement.py completed successfully.")

        # ---------------------------
        # 3. Outlier Analysis (optional)
        # ---------------------------
        if outlier_analysis:
            print("\nRunning outlier_analysis.py ...")
            from outlier_analysis import main as outlier_main

            effective_outlier_settings = _resolve_outlier_settings(
                outlier_settings
            )

            outlier_main(
                input_path=output_csv,
                output_path=outlier_output_name,
                **effective_outlier_settings,
            )
            completed_stages.append("outlier_analysis")
            print("outlier_analysis.py completed successfully.")
        else:
            print("\nOutlier analysis not requested. Skipping outlier_analysis.py.")

        # ---------------------------
        # 4. Report
        # ---------------------------
        print("\nRunning report.py ...")
        from report import main as report_main

        report_main(
            dark_mode=dark_mode,
            summary_path=summary_path,
        )

        completed_stages.append("report")
        print("report.py completed successfully.")

    except Exception as error:
        print("\nPipeline stopped because a follow-up module failed.")
        print(f"Error: {error}")   

        
        # Record partial completion in summary.json before bubbling the error up.
        try:
            if Path(summary_path).exists():
                with Path(summary_path).open("r", encoding="utf-8") as f:
                    summary = json.load(f)
            else:
                summary = {}

            summary["pipeline_completed"] = False
            summary["completed_stages"] = completed_stages
            summary["pipeline_error"] = str(error)
            summary["outlier_settings"] = effective_outlier_settings

            with Path(summary_path).open("w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
        except Exception:
            pass

        raise

    # Update the summary after every requested stage has completed.
    try:
        if Path(summary_path).exists():
            with Path(summary_path).open("r", encoding="utf-8") as f:
                summary = json.load(f)
        else:
            summary = {}

        summary["pipeline_completed"] = True
        summary["completed_stages"] = completed_stages
        summary["pipeline_error"] = None
        summary["outlier_settings"] = effective_outlier_settings

        with Path(summary_path).open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4)
    except Exception as error:
        print(f"Warning: unable to update final summary: {error}")

    result["pipeline_completed"] = True
    result["completed_stages"] = completed_stages
    result["outlier_settings"] = effective_outlier_settings

    print("\nFULL PIPELINE COMPLETED!")
    print(f"Output directory: {output_directory}")

    return result


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as error:
        print(f"\nHyperkey failed: {error}")
        raise SystemExit(1)
