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


def run_pipeline(cli_arguments=None):
    """
    Run the complete Hyperkey workflow.

    This function is the reusable entry point for both:
      - the command-line interface, and
      - the Flet desktop/Android UI.

    The extraction/merge stage remains in main(). Follow-up modules are
    executed here so importing this module runs the same workflow as CLI use.
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

    try:
        # ---------------------------
        # 1. Heatmap
        # ---------------------------
        print("\nRunning visualise_heatmap.py ...")
        from visualise_heatmap import main as heatmap_main

        heatmap_arguments = {
            "input_path": output_csv,
            # "output_name": heatmap_output_name,
            "output_name": None,
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
            # output_name=spectral_graph_output_name,
            # output_name=None,
            output_name="Spectral_graph",
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

            # Expected outlier module contract:
            # main(input_path=None, output_name=None, dark_mode=True)
            outlier_main(
                input_path=output_csv,
                output_name=outlier_output_name,
                dark_mode=dark_mode
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

        # Keep the report module on the same generated-output theme setting.
        # report_main(dark_mode=dark_mode)
        report_main()
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

        with Path(summary_path).open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4)
    except Exception as error:
        print(f"Warning: unable to update final summary: {error}")

    result["pipeline_completed"] = True
    result["completed_stages"] = completed_stages

    print("\nFULL PIPELINE COMPLETED!")
    print(f"Output directory: {output_directory}")

    return result


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as error:
        print(f"\nHyperkey failed: {error}")
        raise SystemExit(1)

