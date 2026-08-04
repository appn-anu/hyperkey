import json
from pathlib import Path
import markdown
import fitz

import load_data as ld
from datetime import datetime
from playwright.sync_api import sync_playwright

# This method loads the summary.json file that has success matrix and visual data path
# report_ddmmyyyy for without custom_output_name
# -o customOutputName_report_ddmmyyyy with custom_output_name

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



from datetime import datetime

def get_report_filename(data, extension):
    timestamp = datetime.strptime(
        data["timestamp"],
        "%Y-%m-%d %H:%M:%S"
    )

    date = timestamp.strftime("%d%m%Y")

    output_name = data.get("custom_output_name")

    if output_name:
        return f"{output_name}_report_{date}.{extension}"

    return f"report_{date}.{extension}"

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

    report_path = project_root / "data" / "output_data" / get_report_filename(data, "md")

    with open(report_path, "w", encoding="utf-8") as file:
        file.write(report_text)

    print(f"Markdown report saved to: {report_path}")

    return report_text

# This method uses the markdown file to generate the html file saves it in the 
# output_data directory 
def generate_html_report(data, report_text, project_root):
    html_body = markdown.markdown(report_text, extensions=["tables"])
    


    html_text = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HyperKey Processing Report</title>

    <style>
    
    
        body {{
            font-family: "Arial", sans-serif;
            background-color: #121212;
            color: #e8e8e8;
            max-width: 950px;
            margin: auto;
            padding: 40px;
            line-height: 1.7;
        }}

        h1 {{
        color: #66d9ef;
        border-bottom: 2px solid #2d2d2d;
        padding-bottom: 10px;
        }}

        h2 {{
        color: #7dd3fc;
        margin-top: 35px;
        page-break-after: avoid;
        }}

        h3 {{
        color: #c084fc;
        page-break-after: avoid;
        }}

        table {{
        width: 60%;
        border-collapse: collapse;
        margin: 20px 0;
        }}

        th {{
        
        background-color: #1e293b;
        color: white;
        }}

        td {{
        background-color: #1a1a1a;
        }}

        th, td {{
        border: 1px solid #333;
        padding: 10px;
        text-align: left;
        }}

        tr:nth-child(even) td {{
        background-color: #202020;
        }}



        img {{
            max-width: 90%;
            height: auto;
            display: block;
            margin: 40px auto;
            border-radius: 8px;
            border: 1px solid #444;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
            page-break-after: avoid;

        }}


        code {{
        background: #222;
        padding: 2px 5px;
        border-radius: 4px;
        }}

        a {{
        color: #4fc3f7;
        }}

    
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""

    html_path = project_root / "data" / "output_data" / get_report_filename(data, "html")

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


def generate_pdf_report(data, project_root):
    output_dir = project_root / "data" / "output_data"

    html_path = output_dir / get_report_filename(data, "html")
    pdf_path = output_dir / get_report_filename(data, "pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page()

        page.goto(
            f"file:///{html_path}",
            wait_until="networkidle"
        )

        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "40px",
                "bottom": "40px",
                "left": "40px",
                "right": "40px"

            }
        )

        browser.close()

    print(f"PDF report saved to: {pdf_path}")

# This main function takes summary.json and generates all three types of reports and 
# saves them in the output_data directory
def main():
    project_root = ld.get_project_root()

    data = load_summary_json(project_root)

    report_text = generate_markdown_report(data, project_root)

    generate_html_report(data, report_text, project_root)

    generate_pdf_report(data, project_root)


if __name__ == "__main__":
    main()