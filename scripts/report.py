import csv
import os
import sys
import argparse
import json
import load_data as ld
from datetime import datetime


project_root = ld.get_project_root()
json_path = project_root / "data" / "output_data" / "summary.json"
with open(json_path, 'r') as file:
    data = json.load(file)

visual_section = ""
if "visualisations" in data and data["visualisations"]:
    for item in data["visualisations"]:
        title = item["title"]
        path = item["path"]

        visual_section += f"""
###{title}
![{title}]({path})
"""
        
else: 
    visual_section = "No visualisation generated yet."


spectral_graph = ""
if "spectral_image" in data and data["spectral_image"]:
    for item in data["spectral_image"]:
        title = item["title"]
        path = item["path"]
        spectral_graph += f"""
###{title}
![{title}]({path})
"""
        
else: 
    spectral_graph = "No spectral graph generated yet."


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

This section includes:
{visual_section}
{spectral_graph}
"""

report_path = project_root / "data" / "output_data" / "report.md"

with open(report_path, "w") as file:
    file.write(report_text)


