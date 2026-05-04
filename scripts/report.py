import csv
import os
import sys
import argparse
import json
from datetime import datetime


with open('data\\output_data\\summary.json', 'r') as file:
    data = json.load(file)

report_text = f"""
# HyperKey Processing Report

Generated: {data["timestamp"]}

## Processing Summary

| Metric | Value |
|---|---:|
| Total rows in metadata | {data["total_rows"]} |
| Successfully matched files | {data["matched_files"]} |
| Blank FileNum rows | {data["blank_filenum"]} |
| Invalid FileNum rows | {data["invalid_filenum"]} |
| Missing .sig files | {data["missing_sig_files"]} |

## Generated Files

- Merged CSV: {data["output_csv"]}
- Log file: {data["log_file"]}

## Visualisations

Visualisations are not generated yet. This section will later include:
- NDVI heatmap
- Spectral graphs
"""

report_path = os.path.join("data", "output_data", "report.md")

with open(report_path, "w") as file:
    file.write(report_text)


