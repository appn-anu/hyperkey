# Hyperkey

HyperKey is a fast leaf-level hyperspectral data review tool for creating visualisations from measurements taken with an SVC HR i series. This is a currently a CLI tool with plans to become a mobile app in the future. It takes in a folder of .sig measurements and one or multiple metadata csv files and outputs a data report to easily visualise the data.

## How to use HyperKey

Current implementation (to be updated as the project evolves):

Run extractMetadata.py and follow the required inputs:

- Select Metadata CSV
- Select Root Folder for .sig files
- Additional Configuration (prefixes, dates, output filename etc.)

Formatted output csv will be generated in the current folder.

## Input formatting

Example raw .sig file data can be found in [raw_data](data/raw_data)

Example metadata csv file can be found in input_csv (not available)

Example Location file can be found in location_csv (not available)
