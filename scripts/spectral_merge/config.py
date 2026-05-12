from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def get_log_timestamp() -> str:
    """Return a readable timestamp for logs and summaries."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ProjectPaths:
    """Common project directories and output locations."""

    script_dir: str
    project_root: str
    processed_dir: str
    raw_dir: str
    default_output_dir: str
    output_csv: str
    log_path: str
    summary_path: str


@dataclass
class RunConfig:
    """Runtime configuration selected from CLI args or interactive prompts."""

    metadata_files: list[str]
    root_folder: str = "."
    output_csv: Optional[str] = None


@dataclass
class RunStats:
    """Counters collected during processing."""

    total_rows: int = 0
    processed_count: int = 0
    skipped_blank: int = 0
    skipped_invalid_format: int = 0
    skipped_missing_file: int = 0
    log_entries: list[str] = field(default_factory=list)

    @property
    def warnings_count(self) -> int:
        return len(self.log_entries)
