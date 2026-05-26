import json
from pathlib import Path
import markdown
import fitz

import load_data as ld

# This method loads the summary.json file that has success matrix and visual data path
def load_summary_json(project_root):
    json_path = project_root / "data" / "output_data" / "summary.json"

    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)

# This method parses the image data present in the summary.json and extract the image path 
# and title. 
def build_image_section(data, key, empty_message):
    section = ""

    if key in data and data[key]:
        for item in data[key]:
            title = item["title"]
            path = item["path"]

            section += f"""
### {title}

![{title}]({path})
"""
    else:
        section = empty_message

    return section

# This method generates the markdown file from the data available from json file and saves it in the 
# output_data directory
def generate_markdown_report(data, project_root):
    visual_section = build_image_section(
        data,
        "visualisations",
        "No visualisation generated yet."
    )

    spectral_graph = build_image_section(
        data,
        "spectral_image",
        "No spectral graph generated yet."
    )

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

    with open(report_path, "w", encoding="utf-8") as file:
        file.write(report_text)

    print(f"Markdown report saved to: {report_path}")

    return report_text

# This method uses the markdown file to generate the html file saves it in the 
# output_data directory 
def generate_html_report(report_text, project_root):
    html_body = markdown.markdown(report_text, extensions=["tables"])

    html_text = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HyperKey Processing Report</title>

    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: auto;
            padding: 20px;
            line-height: 1.6;
        }}

        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""

    html_path = project_root / "data" / "output_data" / "report.html"

    with open(html_path, "w", encoding="utf-8") as file:
        file.write(html_text)

    print(f"HTML report saved to: {html_path}")

# This function is trying to find the correct location of an image file 
# based on the path stored in image_path_value.
def resolve_image_path(image_path_value, project_root, output_dir):
    image_path = Path(image_path_value)

    if image_path.is_absolute():
        return image_path

    possible_project_path = project_root / image_path

    if possible_project_path.exists():
        return possible_project_path

    possible_output_path = output_dir / image_path.name

    return possible_output_path

# This method generates a pdf from the json file and saves it in the 
# output_data directory
def generate_pdf_from_json(data, project_root):
    output_dir = project_root / "data" / "output_data"
    pdf_path = output_dir / "report.pdf"

    doc = fitz.open()
    page = doc.new_page()

    y = 50
    margin = 50

    def add_text(text, size=11, gap=18):
        nonlocal y, page

        if y > 760:
            page = doc.new_page()
            y = 50

        page.insert_text(
            (margin, y),
            str(text),
            fontsize=size,
            fontname="helv"
        )

        y += gap

    def add_image(image_path_value, title):
        nonlocal y, page

        image_path = resolve_image_path(
            image_path_value,
            project_root,
            output_dir
        )

        if not image_path.exists():
            add_text(f"Image missing: {image_path_value}")
            return

        if y > 500:
            page = doc.new_page()
            y = 50

        add_text(title, size=13, gap=20)

        rect = fitz.Rect(margin, y, 545, y + 250)

        page.insert_image(
            rect,
            filename=str(image_path),
            keep_proportion=True
        )

        y += 280

    add_text("HyperKey Processing Report", size=20, gap=30)
    add_text(f"Generated: {data['timestamp']}", gap=25)

    add_text("Processing Summary", size=15, gap=25)
    add_text(f"Total rows in metadata: {data['total_rows']}")
    add_text(f"Successfully matched files: {data['matched_files']}")
    add_text(f"Blank FileNum rows: {data['blank_filenum']}")
    add_text(f"Invalid FileNum rows: {data['invalid_filenum']}")
    add_text(f"Missing .sig files: {data['missing_sig_files']}", gap=25)

    add_text("Generated Files", size=15, gap=25)
    add_text(f"Merged CSV: {data['output_csv']}")
    add_text(f"Log file: {data['log_file']}", gap=25)

    add_text("Visualisations", size=15, gap=25)

    for item in data.get("visualisations", []):
        add_image(item["path"], item["title"])

    for item in data.get("spectral_image", []):
        add_image(item["path"], item["title"])

    doc.save(pdf_path)
    doc.close()

    print(f"PDF report saved to: {pdf_path}")

# This main function takes summary.json and generates all three types of reports and 
# saves them in the output_data directory
def main():
    project_root = ld.get_project_root()

    data = load_summary_json(project_root)

    report_text = generate_markdown_report(data, project_root)

    generate_html_report(report_text, project_root)

    generate_pdf_from_json(data, project_root)


if __name__ == "__main__":
    main()