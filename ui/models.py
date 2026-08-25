from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HyperkeyRunConfig:
    """Values collected from the normal Flet form."""

    metadata_files: list[str] = field(default_factory=list)
    root_folder: str = ""
    raw_location_path: str = ""

    # Output settings are intentionally kept separate:
    #   output_directory -> -o / --output
    #   output_name      -> -n / --name
    output_name: str = ""
    output_directory: str = ""

    dark_mode: bool = True
    outlier_analysis: bool = False

    # UI-only outlier overrides. Empty strings mean "use stored default".
    # These values are NOT converted into CLI arguments.
    outlier_sd_threshold: str = ""
    outlier_max_outliers: str = ""
    outlier_id_column: str = ""
    outlier_group_by: str = ""
    outlier_min_valid_values: str = ""
    outlier_ddof: str = ""


@dataclass
class RunResult:
    """UI-friendly result object used before and after backend integration."""

    success: bool
    message: str
    arguments: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
