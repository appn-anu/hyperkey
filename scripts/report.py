import csv
import os
import sys
import argparse
import json
import load_data as ld
from datetime import datetime
import markdown
import fitz



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


html_body = markdown.markdown(report_text, extensions=["tables"])

html_text = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HyperKey Processing Report</title>
</head>
<body>
{html_body}
</body>
</html>
"""

html_path = project_root / "data" / "output_data" / "report.html"

with open(html_path, "w", encoding="utf-8") as file:
    file.write(html_text)


def generate_pdf_from_json(data, project_root):
    output_dir = project_root / "data" / "output_data"
    pdf_path = output_dir / "report.pdf"

    doc = fitz.open()
    page = doc.new_page()

    y = 50
    margin = 50

    def add_text(text, size=11, bold=False, gap=18):
        nonlocal y, page

        if y > 760:
            page = doc.new_page()
            y = 50

        font = "helv"
        page.insert_text(
            (margin, y),
            text,
            fontsize=size,
            fontname=font
        )
        y += gap

    def add_image(image_filename, title):
        nonlocal y, page

        image_path = output_dir / image_filename

        if not image_path.exists():
            add_text(f"Image missing: {image_filename}")
            return

        if y > 500:
            page = doc.new_page()
            y = 50

        add_text(title, size=13, gap=20)

        rect = fitz.Rect(margin, y, 545, y + 250)
        page.insert_image(rect, filename=str(image_path), keep_proportion=True)

        y += 280

    add_text("HyperKey Processing Report", size=20, gap=30)
    add_text(f"Generated: {data['timestamp']}", size=11, gap=25)

    add_text("Processing Summary", size=15, gap=25)
    add_text(f"Total rows in metadata: {data['total_rows']}")
    add_text(f"Successfully matched files: {data['matched_files']}")
    add_text(f"Blank FileNum rows: {data['blank_filenum']}")
    add_text(f"Invalid FileNum rows: {data['invalid_filenum']}")
    add_text(f"Missing .sig files: {data['missing_sig_files']}", gap=25)

    add_text("Generated Files", size=15, gap=25)
    add_text(f"Merged CSV: {data['output_csv']}", size=11)
    add_text(f"Log file: {data['log_file']}", size=11, gap=25)

    add_text("Visualisations", size=15, gap=25)

    for item in data.get("visualisations", []):
        add_image(item["path"], item["title"])

    for item in data.get("spectral_image", []):
        add_image(item["path"], item["title"])

    doc.save(pdf_path)
    doc.close()

    print(f"PDF saved to: {pdf_path}")


generate_pdf_from_json(data, project_root)
