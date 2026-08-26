from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

from .models import HyperkeyRunConfig, RunResult


BackendRunner = Callable[
    [list[str], dict[str, object] | None],
    dict[str, object] | None,
]


class PipelineService:
    """
    Boundary between the Flet UI and Hyperkey's processing backend.

    By default this service connects to ui.backend.run_hyperkey_backend(),
    so both the friendly form and CLI fallback execute the same workflow.
    A custom backend_runner can still be supplied for testing.

    Outlier tuning values from the friendly form are passed separately from
    CLI arguments. This keeps Hyperkey's public CLI unchanged.
    """

    def __init__(self, backend_runner: BackendRunner | None = None):
        if backend_runner is None:
            from .backend import run_hyperkey_backend
            backend_runner = run_hyperkey_backend

        self.backend_runner = backend_runner

    @staticmethod
    def validate(config: HyperkeyRunConfig) -> list[str]:
        errors: list[str] = []

        if not config.metadata_files:
            errors.append("Select or enter at least one metadata CSV file.")

        if not config.root_folder.strip():
            errors.append("Enter the raw spectral-data root folder.")

        sd_threshold = config.outlier_sd_threshold.strip()
        if sd_threshold:
            try:
                if float(sd_threshold) <= 0:
                    errors.append("Outlier SD threshold must be greater than 0.")
            except ValueError:
                errors.append("Outlier SD threshold must be a number.")

        max_outliers = config.outlier_max_outliers.strip()
        if max_outliers and max_outliers.lower() not in {"none", "all"}:
            try:
                if int(max_outliers) < 1:
                    errors.append("Maximum outliers must be at least 1, or None/all.")
            except ValueError:
                errors.append("Maximum outliers must be a whole number, or None/all.")

        min_valid_values = config.outlier_min_valid_values.strip()
        if min_valid_values:
            try:
                if int(min_valid_values) < 2:
                    errors.append("Minimum valid values must be at least 2.")
            except ValueError:
                errors.append("Minimum valid values must be a whole number.")

        ddof = config.outlier_ddof.strip()
        if ddof:
            try:
                if int(ddof) < 0:
                    errors.append("DDOF cannot be negative.")
            except ValueError:
                errors.append("DDOF must be a whole number.")

        return errors

    @staticmethod
    def build_arguments(config: HyperkeyRunConfig) -> list[str]:
        """
        Translate the friendly UI form into Hyperkey CLI-style arguments.

        Output directory and output name are intentionally kept separate:
          -o / --output -> output directory
          -n / --name   -> optional output-name prefix
        """
        args: list[str] = []
        args.extend(path.strip() for path in config.metadata_files if path.strip())

        if config.root_folder.strip():
            args.extend(["-r", config.root_folder.strip()])

        if config.output_directory.strip():
            args.extend(["-o", config.output_directory.strip()])

        if config.output_name.strip():
            args.extend(["-n", config.output_name.strip()])

        if config.raw_location_path.strip():
            args.extend(["-l", config.raw_location_path.strip()])

        # Existing pipeline semantics: dark mode is the default and -d disables it.
        if not config.dark_mode:
            args.append("-d")

        # The six detailed outlier settings are intentionally NOT CLI arguments.
        if config.outlier_analysis:
            args.append("--outlier-analysis")

        return args

    @staticmethod
    def build_outlier_settings(config: HyperkeyRunConfig) -> dict[str, object]:
        """
        Build UI-only outlier overrides.

        Missing fields are omitted so workflow.py/outlier_analysis.py remains the
        source of truth for defaults.
        """
        settings: dict[str, object] = {}

        sd_threshold = config.outlier_sd_threshold.strip()
        if sd_threshold:
            settings["sd_threshold"] = float(sd_threshold)

        max_outliers = config.outlier_max_outliers.strip()
        if max_outliers:
            if max_outliers.lower() in {"none", "all"}:
                settings["max_outliers"] = None
            else:
                settings["max_outliers"] = int(max_outliers)

        id_column = config.outlier_id_column.strip()
        if id_column:
            settings["id_column"] = id_column

        group_by = config.outlier_group_by.strip()
        if group_by:
            if group_by.lower() in {"none", "no grouping", "no-grouping"}:
                settings["group_by"] = None
            else:
                settings["group_by"] = group_by

        min_valid_values = config.outlier_min_valid_values.strip()
        if min_valid_values:
            settings["min_valid_values"] = int(min_valid_values)

        ddof = config.outlier_ddof.strip()
        if ddof:
            settings["ddof"] = int(ddof)

        return settings

    @staticmethod
    def format_command(arguments: list[str]) -> str:
        def quote(value: str) -> str:
            if not value:
                return '""'
            if any(ch.isspace() for ch in value) or any(ch in value for ch in '"&()'):
                return f'"{value.replace(chr(34), chr(92) + chr(34))}"'
            return value

        rendered = " ".join(quote(str(arg)) for arg in arguments)
        return f"python hyperkey.py {rendered}".rstrip()

    @staticmethod
    def parse_cli_text(raw_text: str) -> list[str]:
        """
        Accept either arguments only or a full command such as:

            metadata.csv -r raw_data
            python hyperkey.py metadata.csv -r raw_data
            hyperkey.py metadata.csv -r raw_data
        """
        text = raw_text.strip()
        if not text:
            return []

        # Windows paths are safer with posix=False; POSIX/mobile paths prefer True.
        looks_windows = "\\" in text or (len(text) >= 2 and text[1] == ":")
        tokens = shlex.split(text, posix=not looks_windows)
        tokens = [token.strip('"\'') for token in tokens]

        if not tokens:
            return []

        first = Path(tokens[0]).name.lower()
        if first in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
            tokens = tokens[1:]

        if tokens and Path(tokens[0]).name.lower() in {"hyperkey", "hyperkey.py"}:
            tokens = tokens[1:]

        return tokens

    def run_arguments(
        self,
        arguments: list[str],
        outlier_settings: dict[str, object] | None = None,
    ) -> RunResult:
        if not arguments:
            return RunResult(False, "No Hyperkey arguments were supplied.")

        if self.backend_runner is None:
            return RunResult(
                success=False,
                message="Hyperkey backend runner is unavailable.",
                arguments=arguments,
                logs=["ERROR: Hyperkey backend runner is unavailable."],
            )

        try:
            backend_result = self.backend_runner(arguments, outlier_settings) or {}

            # ui/backend.py places generated error_log.txt lines under "_logs".
            # Keep those out of the Results summary and surface them in Logs.
            backend_logs = backend_result.pop("_logs", [])
            if not isinstance(backend_logs, list):
                backend_logs = [str(backend_logs)]

            logs = ["Pipeline completed successfully."]
            logs.extend(str(line) for line in backend_logs)

            return RunResult(
                success=True,
                message="Hyperkey processing completed.",
                arguments=arguments,
                summary=dict(backend_result),
                logs=logs,
            )
        except Exception as exc:  # UI boundary: show backend errors instead of crashing.
            return RunResult(
                success=False,
                message=f"Hyperkey processing failed: {exc}",
                arguments=arguments,
                logs=[f"ERROR: {exc}"],
            )

    def run_config(self, config: HyperkeyRunConfig) -> RunResult:
        errors = self.validate(config)
        if errors:
            return RunResult(False, "\n".join(errors), logs=errors)

        outlier_settings = None
        if config.outlier_analysis:
            outlier_settings = self.build_outlier_settings(config)

        return self.run_arguments(
            self.build_arguments(config),
            outlier_settings=outlier_settings,
        )
