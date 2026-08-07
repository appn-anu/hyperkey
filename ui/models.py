from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath


@dataclass
class HyperkeyRunConfig:
    """Values collected from the normal Flet form."""

    metadata_files: list[str] = field(default_factory=list)
    root_folder: str = ""
    raw_location_path: str = ""
    output_name: str = ""
    output_directory: str = ""
    dark_mode: bool = True
    outlier_analysis: bool = False

    def output_argument(self) -> str | None:
        """Return the value that should eventually be passed to -o/--output."""
        name = self.output_name.strip()
        directory = self.output_directory.strip()

        if not name and not directory:
            return None

        if directory and name:
            # Preserve Windows separators even when a Windows path is typed on
            # another platform (useful when commands are being prepared/shared).
            if "\\" in directory or (len(directory) >= 2 and directory[1] == ":"):
                return str(PureWindowsPath(directory) / name)
            return str(Path(directory) / name)

        # If only one is supplied, preserve it rather than inventing a value.
        return name or directory


@dataclass
class RunResult:
    """UI-friendly result object used before and after backend integration."""

    success: bool
    message: str
    arguments: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
