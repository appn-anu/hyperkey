# Hyperkey

HyperKey is a fast leaf-level hyperspectral data review tool for creating visualisations from measurements taken with an SVC HR i series. This is a currently a CLI tool with plans to become a mobile app in the future. It takes in a folder of .sig measurements and one or multiple metadata csv files and outputs a data report to easily visualise the data.

## Basic use of HyperKey

### Clone the Repository

First, clone the HYPERKEY Git repository:

git clone <https://github.com/appn-anu/hyperkey.git>

Navigate to the project folder.

### Prepare the Input Files

The system requires two primary inputs:

- Metadata CSV file
- Raw hyperspectral .sig measurement files

Recommended folder structure:

```text
hyperkey
│
├── data
│   ├── raw_data
│   │   └── .sig files or folders containing .sig files
│   │
│   ├── processed_data
│   │   └── metadata CSV files
│   │
│   └── output_data
│       └── generated outputs
│
└── scripts
    └── pipeline.py
```

Place the required files as follows:

- Add the root folder containing the .sig files, or the .sig files themselves, into data/raw_data/ (optional but recommended).
- Add the metadata sheet in CSV format into data/processed_data/.

Using this structure enables easier use of the interactive command line interface.

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

Notes:

- Subfolder can be omitted if all .sig files are located inside a single root folder.
- If a prefix is not provided, the system assumes the default prefix HR.

## Running the System (interactive)

If the terminal is opened inside the scripts directory, run:

python pipeline.py

This launches the command line interface (CLI).
If the recommended folder structure is followed, the terminal will prompt the user to:

1. Select the metadata CSV file.
2. Select the root folder containing the .sig files.

Once selected, the pipeline automatically executes.

## Running the System (CLI)

The system can also be executed directly using command line arguments.
From the project root:

python "HyperkeyProjectPath/scripts/pipeline.py" "HyperkeyprojectPath/data/processed_data/GH7-test-SubFolder.csv" -r "data/raw_data" -o "mergedTest.csv"

From the scripts directory:

python pipeline.py "../data/processed_data/GH7-test-SubFolder.csv" -r "../data/raw_data" -o "mergedTest.csv"

Using absolute / full file paths (supported irrespective of file location):

python pipeline.py "D:/Experiments/Metadata/GH7-test.csv" -r "D:/Research/Raw_SIG_Files/" -o "D:/Results/mergedTest.csv"

### Command Line Arguments

`pipeline.py` is the main program that runs the complete HYPERKEY application.
The supported arguments are:

#### Metadata File Path

The first positional argument specifies the metadata CSV file path.
The system supports:

- Relative paths
- Absolute/full file paths
- Multiple metadata files separated by spaces

Examples:

python pipeline.py "../data/processed_data/test.csv"

python pipeline.py "D:/Metadata/experiment1.csv"

python pipeline.py "experiment1.csv" "experiment2.csv"

#### -r / --root

Used to specify the root folder path containing:

- .sig files directly, or
- Subfolders containing .sig files.

Supports both relative and full file paths.
Examples:

-r "../data/raw_data"

-r "D:/Research/Raw_SIG_Files/"

#### -o / --output (Optional)

Used to specify the required output merged CSV filename.
Example:
-o "mergedTest.csv"

This is useful when scientists want to clearly label or distinguish outputs from specific experiments.
The argument supports:

- Filename only (mergedTest.csv)
→ Saved inside the project's output directory.
- Relative file path
- Complete / absolute output file path

Examples:
-o "mergedTest.csv"

-o "../results/mergedTest.csv"

-o "D:/Results/Experiment_12_Output.csv"

## Input formatting

Example raw .sig file data can be found in [raw_data](data/raw_data/2026-03-24-S1-Techlauncher/)

Example metadata csv file can be found in [processed_data](data\processed_data\GH7-test-SubFolder.csv)

Example Location file can also be found in [processed_data](data\processed_data\GH7-test-wheats-positions.csv)

## Installation Instructions

- Make sure you have Python 3.11+ installed. 

### Install Dependencies

- To run this project, install the required packages using the main `requirements.txt` file located in the root directory: pip install -r requirements.txt


#### What is being installed:
- Following are the libraries used in this project:
* **`pandas`**: Used for data manipulation, analysis, and structured data tables.
* **`numpy`**: Provides support for large, multi-dimensional arrays and mathematical functions.
* **`matplotlib`**: Handles data visualization and generates plots or charts.
* **`Markdown`**: Parses and converts markdown text into HTML or other formats.
* **`PyMuPDF`**: Enables PDF document parsing, text extraction, and rendering.

#### Verify the Installation

- You can check that your packages were correctly installed by running: 
**`python -c "import pandas, numpy, matplotlib, markdown, fitz; print('All dependencies loaded successfully!')`**




