import json
from pathlib import Path
import markdown
import load_data as ld
from datetime import datetime
from fpdf import FPDF

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
def generate_html_report(data, report_text, project_root, dark_mode):
    html_body = markdown.markdown(report_text, extensions=["tables"])


    if dark_mode:
       
       body_bg = "#121212"
       body_color = "#e8e8e8"
       table_bg = "#1a1a1a"
       heading1 = "#66d9ef"
       heading2 = "#7dd3fc"
       heading3 = "#c084fc"
       border = "#444"
    else:
       body_bg = "white"
       body_color = "black"
       table_bg = "white"
       heading1 = "#0066cc"
       heading2 = "#004c99"
       heading3 = "#663399"
       border = "#cccccc"
    


    html_text = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HyperKey Processing Report</title>

    <style>
    
    
        body {{
            font-family: "Arial", sans-serif;
            background-color: {body_bg};
            color: {body_color};
            max-width: 950px;
            margin: auto;
            padding: 40px;
            line-height: 1.7;
        }}

        h1 {{
        color: {heading1};
        border-bottom: 2px solid #2d2d2d;
        padding-bottom: 10px;
        }}

        h2 {{
        color: {heading2};
        margin-top: 35px;
        page-break-after: avoid;
        }}

        h3 {{
        color: {heading3};
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
        background-color: {table_bg};
        }}

        th, td {{
        border: 1px solid #333;
        padding: 10px;
        text-align: left;
        }}




        img {{
            max-width: 90%;
            height: auto;
            display: block;
            margin: 40px auto;
            border-radius: 8px;
            border: 1px solid {border};
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
    pdf_path = output_dir / get_report_filename(data, "pdf")
    # This is fpdf2
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Report title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "HyperKey Processing Report", new_x="LMARGIN", new_y="NEXT")

    # Generated timestamp
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Generated: {data['timestamp']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Processing Summary
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "Processing Summary", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=11)

    summary_rows = [
        ("Total rows in metadata", data["total_rows"]),
        ("Successfully matched files", data["matched_files"]),
        ("Blank FileNum rows", data["blank_filenum"]),
        ("Invalid FileNum rows", data["invalid_filenum"]),
        ("Missing .sig files", data["missing_sig_files"]),
    ]

    # Table header
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 9, "Metric", border=1)
    pdf.cell(50,9,"Value",border=1,align="R",new_x="LMARGIN",new_y="NEXT")

    # Table rows
    pdf.set_font("Helvetica", size=11)

    for metric, value in summary_rows:
        pdf.cell(120, 9, str(metric), border=1)
        pdf.cell(50, 9, str(value), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)

    # Generated Files
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "Generated Files", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=11)

    pdf.multi_cell(
        0,
        7,
        f"Merged CSV: {data['output_csv']}",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.multi_cell(
        0,
        7,
        f"Log file: {data['log_file']}",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.ln(8)

    # Visualisations
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(
        0,
        10,
        "Visualisations",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    for item in data.get("visualisations", []):
        image_path = resolve_image_path(
            item["path"],
            project_root,
            output_dir
        )

        if image_path.exists():
            pdf.set_font("Helvetica", "B", 12)

            pdf.cell(
                0,
                10,
                item["title"],
                new_x="LMARGIN",
                new_y="NEXT"
            )

            pdf.image(
                str(image_path),
                x=20,
                w=170
            )

            pdf.ln(10)

    # Spectral images
    for item in data.get("spectral_image", []):
        image_path = resolve_image_path(
            item["path"],
            project_root,
            output_dir
        )

        if image_path.exists():
            pdf.set_font("Helvetica", "B", 12)

            pdf.cell(
                0,
                10,
                item["title"],
                new_x="LMARGIN",
                new_y="NEXT"
            )

            pdf.image(
                str(image_path),
                x=20,
                w=170
            )

            pdf.ln(10)

    pdf.output(str(pdf_path))

    print(f"PDF report saved to: {pdf_path}")
    

# This main function takes summary.json and generates all three types of reports and 
# saves them in the output_data directory
def main():
    project_root = ld.get_project_root()

    dark_mode = False

    data = load_summary_json(project_root)

    report_text = generate_markdown_report(data, project_root)

    generate_html_report(data, report_text, project_root, dark_mode)

    generate_pdf_report(data, project_root)


if __name__ == "__main__":
    main()