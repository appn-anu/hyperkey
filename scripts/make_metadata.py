#!/usr/bin/env python3

# Example:
# python scripts/make_metadata.py "data/raw_data/2026-03-24-S1-Techlauncher" out.csv
# python scripts/make_metadata.py "/data/NAR day1" out.csv -r /data --subfolder "NAR day1"
# python scripts/make_metadata.py -h

"""
Generate a Hyperkey metadata CSV from a directory of SVC .sig files.

Datasets do not always arrive with a metadata CSV, and the pipeline cannot run
without one. The pipeline builds each raw filename as
"{Prefix}.{Date}.{FileNum:04d}.sig" (scripts/pipeline.py build_filepath), so
everything the metadata file needs is already recoverable from the filenames
themselves. Anything the .sig header carries that is worth keeping - here the
scan timestamp - goes into Comments.

The generated file is a starting point, not a finished record: Genotype,
Variety and Treatment are placeholders that only a human who was in the field
can fill in. Name is "Sample N" in filename order.

Only plain .sig files are listed. The "_moc" and "_moc_resamp" reprocessed
variants are not addressable through the Prefix/Date/FileNum scheme, so they
are skipped and counted in the summary rather than dropped silently.

Usage:
    make_metadata.py <sig_directory> <output_csv> [-r ROOT] [--subfolder NAME]
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

# HR.091024.0000.sig -> prefix "HR", date "091024", filenum "0000"
SIG_NAME = re.compile(r"^(?P<prefix>.+)\.(?P<date>\d{6})\.(?P<filenum>\d{4})\.sig$")

FIELDNAMES = [
    "Name",
    "Genotype",
    "Variety",
    "Treatment",
    "FileNum",
    "Comments",
    "Date",
    "Prefix",
    "Subfolder",
]


def read_scan_time(path: Path) -> str:
    """Return the first timestamp from the .sig header, or "" if absent."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("time="):
                # "time= 09/10/2024 03:02:34PM, 09/10/2024 03:03:00PM"
                return line.split("=", 1)[1].split(",")[0].strip()

            # The header ends at the "data=" marker; no point scanning 1024
            # bands of spectra looking for a field that is not there.
            if line.startswith("data="):
                break

    return ""


def collect(sig_dir: Path) -> tuple[list[dict], list[str]]:
    """
    Return (entries, skipped) for every file in sig_dir.

    skipped holds the names of .sig files that did not match the pipeline's
    naming scheme, so the caller can say what was left out instead of quietly
    producing a shorter file than the user expected.
    """
    entries = []
    skipped = []

    for path in sorted(sig_dir.iterdir()):
        if not path.is_file():
            continue

        match = SIG_NAME.match(path.name)

        if match is None:
            if path.suffix.lower() == ".sig":
                skipped.append(path.name)

            continue

        entries.append(
            {
                "prefix": match.group("prefix"),
                "date": match.group("date"),
                "filenum": match.group("filenum"),
                "comments": read_scan_time(path),
            }
        )

    return entries, skipped


def resolve_subfolder(sig_dir: Path, root: Path | None, explicit: str) -> str:
    """
    Work out the Subfolder value the pipeline will need.

    The pipeline joins root / Subfolder / filename, so Subfolder has to be the
    sig directory's path relative to the raw-data root. Deriving it from -r is
    less error-prone than typing it, but an explicit --subfolder always wins.
    """
    if explicit:
        return explicit

    if root is None:
        return ""

    try:
        relative = sig_dir.resolve().relative_to(root.resolve())
    except ValueError:
        raise SystemExit(
            f"{sig_dir} is not inside the raw-data root {root}. "
            "Pass --subfolder explicitly if the layout is unusual."
        )

    # "." means the sig files sit directly in the root, which the pipeline
    # represents as an empty Subfolder (see pipeline.normalise_subfolder).
    text = relative.as_posix()

    return "" if text == "." else text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sig_directory", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument(
        "-r",
        "--root",
        type=Path,
        default=None,
        help=(
            "Raw-data root the pipeline will be given. The Subfolder column is "
            "derived from the sig directory's path relative to it."
        ),
    )
    parser.add_argument(
        "--subfolder",
        default="",
        help="Set the Subfolder column directly, overriding --root.",
    )
    arguments = parser.parse_args()

    if not arguments.sig_directory.is_dir():
        print(f"Not a directory: {arguments.sig_directory}")
        return 1

    subfolder = resolve_subfolder(
        arguments.sig_directory, arguments.root, arguments.subfolder
    )

    entries, skipped = collect(arguments.sig_directory)

    if not entries:
        print(f"No .sig files matched in {arguments.sig_directory}")
        return 1

    prefixes = {entry["prefix"] for entry in entries}
    dates = {entry["date"] for entry in entries}

    mixed = len(prefixes) > 1 or len(dates) > 1

    if mixed:
        print(
            "Warning: mixed prefixes or dates found "
            f"({sorted(prefixes)}, {sorted(dates)}). "
            "Writing them on every row rather than relying on forward-fill."
        )

    arguments.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(arguments.output_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()

        for index, entry in enumerate(entries):
            # Prefix/Date/Subfolder forward-fill from the first row down, which
            # is how the shipped GH7 metadata file is written.
            first = index == 0

            writer.writerow(
                {
                    "Name": f"Sample {index + 1}",
                    "Genotype": "Unknown",
                    "Variety": "Unknown",
                    "Treatment": "Field",
                    "FileNum": entry["filenum"],
                    "Comments": entry["comments"],
                    "Date": entry["date"] if (first or mixed) else "",
                    "Prefix": entry["prefix"] if (first or mixed) else "",
                    "Subfolder": subfolder if first else "",
                }
            )

    print(f"Wrote {len(entries)} rows to {arguments.output_csv}")
    print(f"  Prefix: {sorted(prefixes)}  Date: {sorted(dates)}")
    print(f"  Subfolder: {subfolder or '(none)'}")

    if skipped:
        print(
            f"  Skipped {len(skipped)} .sig file(s) not matching "
            "Prefix.Date.FileNum.sig, such as the _moc reprocessed variants:"
        )

        for name in skipped[:3]:
            print(f"    {name}")

        if len(skipped) > 3:
            print(f"    ... and {len(skipped) - 3} more")

    print("  Genotype/Variety/Treatment are placeholders - fill them in by hand.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
