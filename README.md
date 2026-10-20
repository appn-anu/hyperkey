# HyperKey

[![CI/CD Tests](https://github.com/appn-anu/hyperkey/actions/workflows/tests.yml/badge.svg)](https://github.com/appn-anu/hyperkey/actions/workflows/tests.yml)

**Leaf-level hyperspectral data processing, visualisation and reporting for plant research.**

HyperKey processes measurements collected using SVC HR i-series spectroradiometers. It matches raw `.sig` measurements with experiment metadata, merges spectral data, generates vegetation-index heatmaps and reflectance graphs, and produces optional outlier analysis and Markdown, HTML and PDF reports.

The project is developed for the **Australian Plant Phenomics Network (APPN), ANU Node**, with a Python command-line interface and a Flet graphical interface. The Windows application is distributed through a Windows `.exe` installer, and the Android application is distributed as an `.apk`.

Keywords: `hyperspectral data`, `leaf reflectance`, `NDVI`, `spectral analysis`, `outlier detection`, `plant phenotyping`, `SVC HR`, `Python`, `Flet`.

## Contents

- [Features](#features)
- [Installation](#installation)
- [Input data](#input-data)
- [Running HyperKey](#running-hyperkey)
- [Generated outputs](#generated-outputs)
- [Architecture](#architecture)
- [Testing and validation](#testing-and-validation)
- [Building and distributing the app](#building-and-distributing-the-app)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [Development history](#development-history)
- [Contributing](#contributing)
- [Team, contact and licence](#team-contact-and-licence)
- [References](#references)

## Features

- Match metadata rows to leaf-level `.sig` measurements, including nested input folders.
- Combine metadata and spectral measurements into a merged CSV.
- Generate NDVI or a selected supported vegetation-index heatmap.
- Plot spectral-reflectance curves.
- Run optional outlier analysis and include results in reports. The outlier settings pane lets scientists adjust detection parameters, experiment with settings and review the resulting automated analysis.
- Optionally use a positional layout CSV to calculate and arrange the NDVI heatmap according to measurement positions.
- Generate Markdown, HTML and PDF reports, a processing summary and diagnostic information.
- Use custom output paths and names.
- Run the processing workflow through the CLI or graphical interface.
- Access generated files through the UI, including platform-dependent Open and Share actions.
- Access in-app help through the circled question-mark icon in the top-right corner.
- Use synchronised theme controls in the top-right corner and Home–Run page; the interface initially follows the system theme.
- Copy a CLI command to reproduce the selected configuration. Run inputs remain selected between runs until replaced or the application is closed.

## Installation

### Install from GitHub Releases

Open [GitHub Releases](https://github.com/appn-anu/hyperkey/releases), select the required release and download the asset for your device. Packaged applications do not require a separate Python installation.

**Windows**

1. Download and run the Windows `.exe` installer.
2. Choose the installation location and complete the setup wizard. Creating a desktop shortcut is optional.
3. Launch HyperKey from the Start Menu, the optional desktop shortcut or the chosen installation directory.

See the [Windows installation video guide](https://www.youtube.com/shorts/HCJNWWI7Orw).

**Android**

1. Download the `.apk` and open it on your device. If prompted, allow APK installation from the application used to open the download.
2. Install and launch HyperKey.
3. Follow the file-access and output-folder setup described under [Android first-run setup](#android-first-run-setup).

### Run from source

Requirements: Python **3.11 or later**, Git, and the dependencies declared in the repository's `requirements.txt`. A virtual environment is recommended.

```bash
git clone https://github.com/appn-anu/hyperkey.git
cd hyperkey
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the main imports:

```bash
python -c "import pandas, numpy, matplotlib, markdown, spyndex, flet, fpdf; print('Dependencies loaded successfully')"
```

| Dependency | Purpose |
| --- | --- |
| pandas | Metadata, tabular processing and CSV outputs |
| NumPy | Numerical operations on spectral measurements |
| Matplotlib | Heatmaps and spectral graphs |
| Markdown | Markdown-to-HTML conversion |
| spyndex | Spectral / vegetation-index calculations |
| Flet | Cross-platform graphical interface |
| fpdf2 | PDF report generation; imported as `fpdf` |

Use the repository's dependency declarations as the authority for package versions and additional platform packages. Build dependencies are separate from the requirements for running the pipeline.

## Input data

Required inputs:

1. At least one metadata CSV; multiple metadata CSVs can be supplied in the same run.
2. A root directory containing SVC `.sig` files.

All selected metadata CSVs share **one raw-data root directory**. Place the measurement datasets beneath a common parent directory and use each CSV’s `Subfolder` values to identify the correct relative locations. Metadata CSVs themselves do not have to reside inside that root. Separate CSV-to-root mappings are not supported.

In the CLI, separate metadata CSV paths with spaces and quote paths containing spaces. In the Windows and Android interfaces, select multiple CSVs together in the file picker.

An optional locations CSV supplies measurement positions for a spatial heatmap. Without suitable location information, do not interpret the heatmap as a confirmed physical layout.

### Metadata CSV

The required headers are:

```csv
FileNum,Date,Prefix,Subfolder
```

The planned metadata header set is shown below. Only `FileNum`, `Date`, `Prefix` and `Subfolder` are required; the remaining fields provide descriptive experiment information.

```csv
Name,Genotype,Variety,Treatment,FileNum,Comments,Date,Prefix,Subfolder
```

**Column naming:** Use descriptive text for non-spectral column headers. Avoid numeric-only headers or headers beginning with a number, because wavelength-column detection may interpret them as spectral wavelengths and mix metadata with spectral data. This restriction concerns column names, not numeric metadata values.

| Field | Meaning |
| --- | --- |
| `FileNum` | Identifies the corresponding measurement file |
| `Date` | Used in measurement filename / path resolution |
| `Prefix` | Used in measurement filename resolution |
| `Subfolder` | Identifies a nested folder under the selected raw-data root |

Blank `Date`, `Prefix` and `Subfolder` values can inherit the preceding row's values in the project's metadata workflow. Provide initial values before relying on inheritance. Set `Subfolder` to the exact relative folder containing the measurements whenever the location changes; subsequent blank cells reuse that value until another non-empty value appears. HyperKey does not automatically search for or infer missing subfolder paths. `FileNum` identifies each measurement and should not be treated as an inherited field.

Use [the supplied metadata example](data/example_data/example1/metadata.csv) for the exact date, prefix and file-number conventions. Preserve identifiers such as leading zeroes where the measurement naming convention requires them. Avoid spreadsheet conversions that alter dates or identifiers.

### Raw measurements

- Supported input: SVC `.sig` measurements from individual leaves.
- Multiple measurement files can be processed in one run.
- Nested folders are resolved using metadata and the selected root directory.
- The selected root must agree with the `Subfolder` paths; avoid repeating a folder segment in both.

Example files: [example1/sig_files](data/example_data/example1/sig_files).

### Optional locations CSV

The example dataset uses [positions.csv](data/example_data/example1/positions.csv). A user-supplied file may also be named `species_locations.csv`; the filename does not define its schema. Follow the supplied example's column format and ensure its identifiers match the measurement data.

### Repository layout

The following lists the documented core paths; generated filenames may vary with settings:

```text
data/example_data/         Example metadata, measurements and locations
scripts/                   Processing, visualisation and reporting modules
ui/                        Graphical interface
tests/                    Automated tests
hyperkey.py                User-facing entry point
requirements.txt           Runtime dependency declarations
```

Inputs do not need to be stored inside the repository. Absolute paths are supported; quote paths containing spaces.

## Running HyperKey

Run the following commands from the **repository root**, unless stated otherwise.

### Graphical interface

```bash
python hyperkey.py
```

1. In **Home–Run**, select one or more metadata CSVs and the single raw measurement root.
2. Add a positional layout CSV if required, then configure output and processing settings.
3. Enable and tune outlier analysis as needed, then select **Run HyperKey**.
4. Review **Results**, **Outputs** and **Log** after processing.

| Page / control | Purpose |
| --- | --- |
| **Home–Run** | Configure all run inputs and processing settings. Values remain unchanged between runs until replaced or the app closes. |
| **CLI** | Run or rerun the application directly using a CLI command. Copy the generated command to reproduce a configuration. |
| **Results** | Review the supplied arguments, generated results, CLI command and captured CLI output for inspection and troubleshooting. |
| **Outputs** | Preview `report.md`, inspect generated file locations and use each file’s Open and Share buttons. |
| **Log** | Review errors and run statistics. |
| **Help** | Open guidance using the circled question-mark icon at the top right. |

The top-right dark-mode switch and the Home–Run theme switch are synchronised. The Home–Run control also determines the theme used when output files are generated. Reports follow the selected UI theme at generation time; switching themes later does not restyle existing reports or visualisations.

### Android first-run setup

At startup, HyperKey requests all-files access and explains that it is needed to access raw-data root folders and write output files to selected locations. Folder-specific access is also requested when a root folder is shared with or selected for the application, providing an additional access check.

On the first run, choose the default output destination. The app recommends a location and allows you to choose your own. **The selected default cannot be changed through the app after it is confirmed.** Use a dedicated `Hyperkey` subfolder within Documents or Downloads, rather than selecting a general-purpose folder directly.

Android’s file-selection flow supplies the selected metadata file’s bytes rather than a direct path to the original document. HyperKey stores those bytes in temporary app storage, so the metadata path displayed in the inputs can look unfamiliar. This temporary path is expected and does not indicate that the source file has moved.

**Reusing CLI commands on Android:** Before rerunning a copied command, update its metadata CSV path to the current temporary copy. Reselect the metadata file if needed; an earlier temporary path may no longer be available.

### Command-line interface

Inspect the flags supported by your checkout:

```bash
python hyperkey.py --help
```

Run an example dataset:

```bash
python hyperkey.py data/example_data/example1/metadata.csv -r data/example_data/example1 --outlier-analysis
```

Process multiple metadata files against one shared root:

```bash
python hyperkey.py "metadata_a.csv" "metadata_b.csv" -r "raw_data" --outlier-analysis
```

Include the optional locations file:

```bash
python hyperkey.py data/example_data/example1/metadata.csv -r data/example_data/example1 -l data/example_data/example1/positions.csv --outlier-analysis
```

Use absolute paths, including a custom output target:

```powershell
python hyperkey.py "D:\Experiments\metadata.csv" -r "D:\Experiments\raw" -l "D:\Experiments\species_locations.csv" -o "D:\Experiments\results\merged_spectral_data.csv" --outlier-analysis
```

| Argument | Purpose |
| --- | --- |
| Metadata positional arguments | One or more metadata CSV paths, separated by spaces |
| `-r` | Raw measurement root directory |
| `-l` | Optional locations CSV |
| `-o` | Custom output target / name; check `--help` for the exact accepted form in your checkout |
| `--outlier-analysis` | Enable outlier analysis |

The examples above reflect the documented project interface. Additional switches and defaults should be checked with `--help`, especially when using an older checkout.

### Backend CLI entry point

To run the backend independently in CLI mode, open a terminal in `scripts` and run `python workflow.py`, supplying the required arguments or following the interactive prompts. Running `hyperkey.py` with CLI arguments invokes the same workflow directly.

```bash
python scripts/workflow.py --help

You can also directly run : 

```bash
python pipeline.py
```

Where prompted, select `0` to enter a path manually, then supply the metadata CSV and raw-data root. This is the extraction entry point; use `hyperkey.py` for the user-facing workflow and report options.

## Generated outputs

| Output | Contents |
| --- | --- |
| `merged_spectral_data.csv` | Metadata combined with extracted spectral measurements |
| `summary.json` | Run statistics and generated file locations; it is a run summary rather than the full scientific report |
| Diagnostic / error log, when emitted | Missing measurements, invalid values and warnings |
| `heatmap.png` | NDVI or the selected supported vegetation-index heatmap |
| `SpectralGraph.png` | Spectral-reflectance curves |
| Outlier CSV and associated outputs, when enabled | Measurement identifiers, comments and relevant statistics |
| Markdown report (`.md`) | Heatmap and spectral-data visualisations, outlier file numbers, relevant paths, comments and other run information |
| HTML report (`.html`) | Browser-readable report with print styling |
| PDF report (`.pdf`) | Shareable report generated using fpdf2 |

Names are representative defaults; custom names and uniqueness handling can change the final filenames. Use the run summary and Outputs view to locate the actual files.

### Output locations

The graphical application's platform-aware storage conventions are:

| Platform | Default application output location |
| --- | --- |
| Windows | `Documents/hyperkey` under the user's profile |
| Android | User-confirmed default folder; a dedicated `Hyperkey` subfolder in Documents or Downloads is recommended |
| Linux / macOS | `~/Hyperkey` |

Older scripts or checkouts may use `data/output_data`. Where supported, a selected custom output destination overrides the applicable default. On Android, the first-run default folder is fixed after confirmation; use the destinations offered by the app for subsequent runs. The CLI, UI and packaged app may resolve defaults differently; check the reported output paths for the run.

Keep reports with their associated images when the HTML uses relative image references. For Android viewing, generated local image paths must be accessible to the viewer; see troubleshooting.

## Architecture

| Component | Responsibility |
| --- | --- |
| `hyperkey.py` | User-facing entry point |
| `ui/` | Flet controls, settings, help and output access |
| `scripts/workflow.py` | Backend entry point: coordinates modules, handles CLI behaviour and prompts for valid input types, validates input data and files, and passes the required data to visualisation and reporting modules |
| `scripts/pipeline.py` | Validates metadata, locates measurements and merges spectral data |
| `scripts/visualise_heatmap.py` | Calculates the selected index and generates the heatmap |
| `scripts/visualise_measurement.py` | Generates spectral-reflectance graphs |
| `scripts/outlier_analysis.py` | Detects and exports unusual measurements |
| `scripts/report.py` | Generates Markdown, HTML and PDF reports |

Workflow:

1. Validate input paths and metadata.
2. Resolve and read matching `.sig` measurements.
3. Merge metadata and spectra and record processing results.
4. Generate index heatmaps and spectral graphs.
5. Run optional outlier analysis.
6. Generate reports and expose output paths.

The shared Python processing workflow supports the CLI and UI. Output paths are coordinated across modules so reports and images use the selected destination.

NDVI is calculated as `(NIR - Red) / (NIR + Red)`, using measured spectral bands nearest the required wavelengths. Inspect wavelength coverage and invalid values before interpreting results. Outlier results identify measurements for review; they do not independently establish plant disease or stress.

## Testing and validation

From the repository root, with pytest and pytest-cov installed:

```bash
python -m pytest --cov=scripts --cov-report=term-missing
```

The documented validation scope includes measurement matching, missing or invalid metadata, output-path handling, index calculations, report generation and outlier exports. Consult the actual tests and CI configuration for current coverage and workflow triggers.

For a release, also manually check:

- Processing with example data and representative researcher data.
- Custom paths, paths containing spaces and repeated runs.
- Consistency of report values and generated visualisations.
- Windows installation and application launch.
- Android processing, report images and Open / Share behaviour.

Automated functional checks do not substitute for scientific validation against researcher-reviewed measurements.

## Building and distributing the app

### Flet builds

Run from the repository root using the project's configured Flet build environment:

```bash
flet build windows .
flet build apk .
flet build aab .
```

Here, `.` selects the current directory as the project source. Build only the required target. The Windows build requires a suitable Windows build environment; Android builds require the appropriate Android tooling. Follow the Flet version and project configuration used by the checkout rather than upgrading dependencies independently.

- **Windows build:** application executable plus supporting runtime files.
- **APK:** Android installation package for direct device installation and testing.
- **AAB:** Android App Bundle intended for store distribution; it is not installed like an APK.

Use the build tool's reported destination to locate artifacts. Signing and release configuration must be completed for the intended distribution channel.

### Windows installer using Inno Setup

The project uses `HyperKeySetup` as the installer output base name.

1. Build the Windows application and confirm it launches from the build directory.
2. Open Inno Setup and start the **Script Wizard** to generate an installer script.
3. Enter application name **HyperKey**, the project's actual version and publisher details. The application website may be the organisation website if no dedicated application site exists.
4. Choose an appropriate installation directory and allow a Start Menu shortcut if desired.
5. Select the built `HyperKey.exe` as the main executable, using its actual build path.
6. In **Other application files**, add the entire Windows build folder, including subfolders and supporting files. Do not package only the executable. If the executable is listed separately, avoid a duplicate installer entry for it.
7. Leave file association disabled unless HyperKey implements opening the chosen file type from an operating-system file association.
8. No separate `.reg` import is needed for the basic installation workflow.
9. Select installer language(s), an output directory outside the input build folder, and output base filename **HyperKeySetup**. A custom installer icon is optional.
10. The wizard's `#define` compiler directives option can be enabled to keep application metadata easy to update.
11. Save the generated `.iss` script, compile it, and test installation, launch and uninstallation on a clean Windows system.

Include any redistributable only when required by the actual build, and follow its distribution terms. Release binaries can be attached to a GitHub Release alongside installation notes and the corresponding source version.

### Android notes

Test file selection, output permissions, report rendering and file sharing on a real device. Android file access depends on device version, application packaging and viewer permissions. Where the application uses a permission-handler extension, include it in the build dependencies.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Measurement files cannot be found | Check `FileNum`, filename conventions, inherited metadata fields, root path and `Subfolder` values |
| A blank metadata value causes a `.strip()` error | Check null-value handling before string operations; validate / normalise optional metadata fields |
| NDVI processing fails on an empty wavelength array | Confirm usable spectral data and wavelength coverage; validate arrays before nearest-band selection |
| HTML images are missing on Android | A local filesystem path may be inaccessible to the HTML viewer. Embed each generated image as a base64 data URI during report generation, or use a viewer-accessible URI. This must happen for each run because images are generated dynamically |
| Android Open fails but Share works | Use Share to open the output in a compatible application; review URI handling and permissions for the Open action |
| `help_item() takes 2 positional arguments but 3 were given` | Align the `_show_help` call with the helper's declared parameters, then rebuild the packaged app |
| Android packaging cannot import a platform extension | Check the extension's inclusion in the project's build dependency configuration |
| Images are missing from a moved HTML report | Keep relative image assets beside the report, or generate a self-contained HTML report |
| Results appear in an unexpected folder | Check custom output settings and the paths in `summary.json` / the Outputs view |

These checks describe issues encountered during development. Their presence here does not imply every issue remains open in the current source version.

## Known limitations

- **Validation with real data:** The system has not yet been validated using real research data, as no such dataset was provided during development.
- **Single raw-data root:** Multiple metadata CSVs, including two CSVs in one run, are supported, but all must share one root folder. Independent mappings such as CSV A → root A and CSV B → root B are not supported. A future extension could combine these separately mapped datasets into one merged CSV and report.
- **Explicit subfolder paths:** Automatic subfolder discovery is not implemented, avoiding additional directory-search overhead and ambiguous matches. Record the exact relative measurement folder in `Subfolder` whenever it changes; blank cells inherit the last specified value.
- **Installation size:** Bundled dependencies, shared libraries and Windows DLLs contribute substantially to storage requirements. Android also includes platform-specific permission-handling code and packages that are absent from the Windows distribution. The current lightweight workflow has not shown a corresponding processing-speed penalty, but this is not a benchmarked performance guarantee. Dependency pruning and more selective packaging could reduce the installation footprint, subject to compatibility testing.
- **Diagnostic clarity:** Some warnings and troubleshooting messages from the pipeline and workflow modules are not sufficiently specific. More actionable messages and clearer identification of the underlying input or processing issue remain improvements.
- **HTML and PDF styling:** Generated HTML and PDF reports have some styling inconsistencies. `fpdf2` does not reproduce all HTML styles, but it was the only suitable option identified during development that supported the project's Python and Android requirements.
- **macOS testing:** The desktop application has been tested on Windows and Linux but remains untested on macOS. macOS support was outside the current development scope.
- **Visualisation readability:** Text becomes harder to read as heatmaps grow. The spectral graph legend is hidden when more than 20 lines are displayed, limiting identification of individual series.
- **Font consistency:** Fonts across visualisations and generated reports are not fully aligned with the application's typography. Standardising them remains a planned improvement.
- **Outlier settings and visualisations:** Adjustments in the outlier settings pane currently apply only to the automated outlier detection and analysis module. Visualisations do not update to reflect those parameters; synchronising them is a planned improvement.
- **iOS distribution:** An iOS version is currently unavailable. The project has not enrolled in the paid Apple Developer Program or configured the required signing for distribution, and an iOS build requires access to macOS.
- **Theme changes after report generation:** Changing light or dark mode updates the interface, but existing reports and visualisations retain their generation-time theme.
- **Acquisition-software integration:** HyperKey currently processes `.sig` files separately from APPN's existing acquisition application on CAT devices. Integration could be explored, but the intended workflow processes batches of hundreds to thousands of samples after acquisition, so immediate per-sample integration is not currently required.

## Development history

The supplied documentation records the following changes; consult [commits](https://github.com/appn-anu/hyperkey/commits/main) and [releases](https://github.com/appn-anu/hyperkey/releases) for source versions and release dates.

### Version 1.0.0 — released

- Windows application distributed through an `.exe` installer.
- Android application distributed as an `.apk`.
- CLI and Flet interface for processing, visualisation, optional outlier analysis and reporting.

### Subsequent development

- Custom output paths and unique output naming.
- Optional outlier analysis and outlier listings in reports.
- Print-friendly HTML styling.
- Replacement of Playwright / Chromium PDF generation with fpdf2.
- Flet desktop / mobile interface, platform-aware output storage and output access.
- Windows installer and Android build workflows.

### Initial prototype

- Metadata-to-measurement matching.
- Merged spectral CSV generation.
- NDVI heatmaps and spectral-reflectance graphs.
- Markdown, HTML and PDF reports.

## Contributing

When reporting an issue, include the source version or packaged release, operating system, command or UI steps, error message, and a small reproducible dataset where sharing is permitted. Remove confidential experiment information before uploading data.

For code changes, explain the expected behaviour, run the relevant tests, and check affected outputs. Platform-related changes should be tested on the affected platform.

## Team, contact and licence

- **Organisation:** Australian Plant Phenomics Network — ANU Node.
- **Stakeholders:** Ming-Dao Chia and Supriyo Shafkat Ahmed.
- **Developers:** Chikith Rishi Maddi, Vishakha Mathur and Samuel Keun.
- **Contact:** Ming-Dao Chia (Ming-Dao.Chia@anu.edu.au).

HyperKey is licensed under the [MIT License](LICENSE), supporting reuse and modification subject to its terms.

## References

- Rouse, J. W., Haas, R. H., Schell, J. A., and Deering, D. W. (1974). *Monitoring Vegetation Systems in the Great Plains with ERTS*. Third Earth Resources Technology Satellite Symposium, NASA SP-351.
- [spyndex documentation](https://spyndex.readthedocs.io/) — spectral-index definitions and package usage.
- [fpdf2 documentation](https://py-pdf.github.io/fpdf2/) — PDF generation.

For reproducible scientific documentation, record the exact SVC instrument manual, index definitions and outlier method / parameters used by the implementation. The supplied README does not identify the instrument manual or outlier algorithm, so no specific source is claimed here.
