# Hyperkey

[![CI/CD Tests](https://github.com/appn-anu/hyperkey/actions/workflows/tests.yml/badge.svg)](https://github.com/appn-anu/hyperkey/actions/workflows/tests.yml)

## Title 
HyperKey - Fast Leaf-Level Hyperspectral Data Processing and Visualization

## Description
HyperKey processes leaf-level hyperspectral measurements collected using
SVC HR i-series spectroradiometers. It combines `.sig` files with experiment
metadata and generates merged data, visualisations, outlier listings and
reports in Markdown, HTML and PDF formats.
It provides a command line interface and a desktop and mobile app (currently under development). 


## Tags and Keywords
`hyperspectral imaging`, `leaf reflectance`, `NDVI`, `spectral analysis`,
`outlier detection`, `SVC HR`, `plant phenotyping`, `Python`

## License
We used [MIT License](LICENSE) because it is simple, permissive and encourages developers and researchers to reuse the software. 

## Authors and Contributors
- Australian Plant Phenomics Network - ANU Node
- Stakeholders: Ming Dao Chia and Supriyo Shafkat Ahmed
- Team Members/Developers: Chikith Rishi Maddi, Vishakha Mathur, Samuel Keun

## Contact
- Ming-Dao Chia (Ming-Dao.Chia@anu.edu.au)

## Installation and Setup

### Requirements 
- Python 3.11 or above. 
- Git

### Installations
- git clone <https://github.com/appn-anu/hyperkey.git>
- Navigate to the project folder. 
- To run this project, install the required packages using the main `requirements.txt` file located in the root directory:

```bash
pip install -r requirements.txt
```
Verify the installation
```bash 
python -c "import pandas, numpy, matplotlib, markdown, spyndex, flet, fpdf; print('Dependencies loaded successfully')"

```
#### What is being installed:
- Following are the libraries used in this project:
* **`pandas`**: Used for data manipulation, analysis, and structured data tables.
* **`numpy`**: Provides support for large, multi-dimensional arrays and mathematical functions.
* **`matplotlib`**: Handles data visualization and generates plots or charts.
* **`Markdown`**: Parses and converts markdown text into HTML or other formats.
* **`Spyndex`**: Calculates the visual index for hyperspectral data reading. 
* **`Flet`**: Used to build interactive, cross-platform UI applications. 
* **`fpdf2`**: Used to generate pdf from markdown file. 

## Expeced Input 

The system requires two primary inputs:

- Metadata CSV file
- Raw hyperspectral .sig measurement files

### Input formatting

- Example raw .sig file data can be found in [sig_files](data/example_data/example1/sig_files)

- Example metadata csv file can be found in [example1](data/example_data/example1/metadata.csv)

- Example Location file can also be found in [example1](data/example_data/example1/positions.csv)


Recommended folder structure:

```text
hyperkey
│
├── data
│   ├── example_data
│   │   └── example .sig, metadata, and location files
|   |   └── where to place .sig files for convenience
│   │   └── where to place metadata/location CSV files for convenience
│   |
│   └── output_data
|       └── images of ndvi heatmap and hyperspectral data
│       └── report.md
|       └── report.html
│       └── report.pdf
|       └── images of outlier data
├── scripts
|    └── pipeline.py
|    └── workflow.py
|
├── tests 
├── ui
├── conftest.py
└── hyperkey.py
    
```


**Note:** The above folder structure is optional. The exact full file path of the metadata file, root folder, and output file can be supplied directly through command line arguments regardless of where the files are stored on the system.

### Metadata File Requirements

The metadata sheet must be provided in CSV format.
Required headers:
FileNum, Date, Prefix, Subfolder
Header description:

- FileNum: Identifies the corresponding measurement file.
- Date: Used during file path and filename resolution.
- Prefix: Used for filename prefixes.
- Subfolder: Used when files are stored inside nested folders.

### Hyperspectral measurements
- Format: SVC .sig
- Source: SVC HR i-series spectroradiometer
- Objects represented: individual leaf measurements
- Multiple .sig files may be provided within one root directory.
- Nested directories are supported through the Subfolder metadata field.

## Output generated
Hyperkey can generate:
- Merged spectral data: CSV metadata combined with spectral measurements. 
- Processing summary: Its in JSON format that runs statistics, paths and completion status. 
- Error log: txt format contains the information of missing files, invalid values and warnings. 
- Heatmap: NDVI or selected vegetation-index visualisation.
- Spectral graph: Reflectance curves for processed measurements. 
- Outlier analysis: Outlier file number, comments, path and statistics. 
- Markdown report: Portable text report. 
- HTML report:	Styled browser report with printing support. 
- PDF report: Shareable report generated using fpdf2. 


## Running the System (interactive)

If the terminal is opened inside the scripts directory, run:

```bash
python pipeline.py
```
This launches the command line interface (CLI).
If the recommended folder structure is followed, the terminal will prompt the user to enter the metadata csv manually (just press 0) and type path of the csv file from the example1/example2 folder. 
The user is later prompted to enter the root folder, press 0 for entering the manually and then type the path when prompted. 
After this, the pipeline automatically executes. You can see the generated outputs in the output_data folder. 

The system can also start web application on desktop from the project root:

```bash
python hyperkey.py
```
Once, the UI comes up, you can select the root folder and the metadata.csv file and run hyperkey button at the bottom. This will run all the scripts in the backend and generate the visualisations and output files. 

From the scripts directory:

```bash

```

Using absolute / full file paths (supported irrespective of file location):

```bash

```

## Sample and Test Data

Example data is available in [`data/example_data`](data/example_data). It contains:

* metadata CSV files;
* SVC `.sig` hyperspectral measurements; and
* location files used to arrange measurements in the heatmap.

Run HyperKey with the example dataset:

```bash
python hyperkey.py data/example_data/example1/metadata.csv \
  -r data/example_data/example1 \
  --outlier-analysis
```

Run the automated test suite after system changes:

```bash
pytest --cov=scripts --cov-report=term-missing
```

These tests verify file matching, path handling, report generation and other expected pipeline behaviour.

## Validation and Quality Assurance

HyperKey currently uses automated tests and manual output inspection for functional validation.

The following checks are performed:

* metadata rows are matched with the expected `.sig` files;
* missing, blank and invalid file numbers are reported;
* output files are created in both default and custom locations;
* NDVI uses the spectral bands nearest to the required red and near-infrared wavelengths;
* Markdown, HTML and PDF reports contain consistent processing results;
* outlier listings are checked against the generated outlier CSV; and
* CI runs the test suite whenever changes are pushed.


## Technical Documentation

HyperKey uses a modular Python workflow:

| Component                  | Responsibility                                                          |
| -------------------------- | ----------------------------------------------------------------------- |
| `hyperkey.py`              | User-facing entry point                                                 |
| `workflow.py`              | Coordinates all processing stages                                       |
| `pipeline.py`              | Validates metadata, finds `.sig` files and creates merged spectral data |
| `visualise_heatmap.py`     | Calculates the selected vegetation index and generates a heatmap        |
| `visualise_measurement.py` | Generates spectral-reflectance graphs                                   |
| `outlier_analysis.py`      | Detects and exports unusual spectral measurements                       |
| `report.py`                | Generates Markdown, HTML and PDF reports                                |

The workflow follows these stages:

1. Validate the supplied paths and metadata.
2. Match metadata rows with `.sig` measurements.
3. Create the merged spectral CSV and processing summary.
4. Generate the heatmap and spectral graph.
5. Run optional outlier analysis.
6. Generate Markdown, HTML and PDF reports.

Output paths are resolved centrally and passed to each module. This allows the same workflow to support both the default output directory and a custom path supplied with `-o`.

## Version History

### Unreleased

* Added custom output paths.
* Added optional outlier analysis.
* Added outlier listings to Markdown, HTML and PDF reports.
* Added print-friendly HTML report styling.
* Replaced Playwright and Chromium with fpdf2 for PDF generation.
* Improved unique output filenames to prevent overwriting.


### Initial Prototype

* Added metadata and `.sig` file matching.
* Added merged spectral CSV generation.
* Added NDVI heatmaps and spectral-reflectance graphs.
* Added basic Markdown, HTML and PDF reports.

For detailed development history, see the repository’s [commit history](https://github.com/appn-anu/hyperkey/commits/main) and [releases](https://github.com/appn-anu/hyperkey/releases).

## References

1. Rouse, J. W., Haas, R. H., Schell, J. A., and Deering, D. W. (1974). *Monitoring Vegetation Systems in the Great Plains with ERTS*. Third Earth Resources Technology Satellite Symposium, NASA SP-351.

2. Montero, D., Aybar, C., Mahecha, M. D., Martinuzzi, F., Söchting, M., and Wieneke, S. (2023). spyndex: A Python package for computing spectral indices. *SoftwareX, 23*, 101341. https://doi.org/10.1016/j.softx.2023.101341

3. spyndex documentation: https://spyndex.readthedocs.io/

4. SVC HR-series spectroradiometer documentation: [add the exact manual or manufacturer URL used by the project].

5. fpdf2 documentation: https://py-pdf.github.io/fpdf2/

6. Outlier-detection method: [add the paper or statistical source corresponding to the method implemented in `outlier_analysis.py`].











