from __future__ import annotations

import os
import shlex
from collections.abc import Callable
from pathlib import Path

from .models import HyperkeyRunConfig, RunResult


BackendRunner = Callable[[list[str]], dict[str, object] | None]


class PipelineService:
    """
    Boundary between the Flet UI and Hyperkey's processing backend.

    By default this service connects to ui.backend.run_hyperkey_backend(),
    so both the friendly form and CLI fallback execute the same workflow.
    A custom backend_runner can still be supplied for testing.
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

        return errors

    @staticmethod
    def build_arguments(config: HyperkeyRunConfig) -> list[str]:
        """Translate the friendly UI form into Hyperkey CLI-style arguments."""
        args: list[str] = []
        args.extend(path.strip() for path in config.metadata_files if path.strip())

        if config.root_folder.strip():
            args.extend(["-r", config.root_folder.strip()])

        output = config.output_argument()
        if output:
            args.extend(["-o", output])

        if config.raw_location_path.strip():
            args.extend(["-l", config.raw_location_path.strip()])

        # Existing pipeline semantics: dark mode is the default and -d disables it.
        if not config.dark_mode:
            args.append("-d")

        # New flag to be added to the backend parser during the pipeline update.
        if config.outlier_analysis:
            args.append("--outlier-analysis")

        return args

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

    def run_arguments(self, arguments: list[str]) -> RunResult:
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
            backend_result = self.backend_runner(arguments) or {}

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
        except SystemExit as exc:
            # argparse calls sys.exit() on bad arguments and on -h/--help.
            # SystemExit is a BaseException, so it would otherwise escape the
            # handler below and kill the worker thread. The UI has its own
            # Help screen, so point users there rather than printing usage.
            return RunResult(
                success=False,
                message=(
                    "Those arguments could not be parsed "
                    f"(argparse exit code {exc.code}). See the Help screen for "
                    "the supported options."
                ),
                arguments=arguments,
                logs=[f"ERROR: invalid arguments (argparse exit code {exc.code})"],
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

        return self.run_arguments(self.build_arguments(config))
