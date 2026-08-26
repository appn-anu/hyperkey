#!/usr/bin/env python3
"""
Outlier analysis for Hyperkey merged hyperspectral CSV data.

Design:
1. Detect wavelength columns automatically from numeric column names.
2. Calculate mean independently for every wavelength.
3. Calculate standard deviation independently for every wavelength.
4. Calculate Z-scores for every valid spectral reading.
5. A file is considered an outlier if at least one wavelength is outside
   +/- DEFAULT_SD_THRESHOLD standard deviations from that wavelength mean.
6. Each outlier file appears only once in the output.
7. The output keeps all non-wavelength columns from the merged spectral CSV.
8. Only compact calculation summary fields are added:
      - OutlierPointCount
      - AverageAbsSD
      - MaxAbsSD
9. Optional grouping and output limiting are retained as tunable settings.

All tunable settings are kept in this file only.
"""

from pathlib import Path

import pandas as pd


# ============================================================
# Default Outlier Settings
# ============================================================

# A spectral reading is considered an outlier when its absolute
# Z-score is greater than this threshold.
DEFAULT_SD_THRESHOLD = 2

# Maximum number of unique outlier files written to the final output.
# Set to None if all detected outlier files should be written.
DEFAULT_MAX_OUTLIERS = 20

# Unique identifier column used to identify each file.
DEFAULT_ID_COLUMN = "FileNum"

# Optional metadata column used to organise/group the output.
# Examples: "Name", "Genotype", "Variety", "Treatment"
# Use None for no grouping.
DEFAULT_GROUP_BY = None

# Minimum number of valid readings required at a wavelength before
# that wavelength is included in outlier detection.
DEFAULT_MIN_VALID_VALUES = 2

# ddof=1 calculates sample standard deviation.
DEFAULT_DDOF = 1


# ============================================================
# Column Identification / Data Preparation
# ============================================================

def identify_wavelength_columns(df):
    """
    Identify all wavelength columns.

    Handles:
    - Normal wavelength columns:
        339.1
        994.0
        1009.3

    - Duplicate wavelength columns renamed by pandas:
        994.0.1
        1009.3.1

    These are all treated as spectral columns and therefore excluded
    from the final outlier output.
    """
    wavelength_columns = []

    for column in df.columns:
        column_name = str(column).strip()

        # Normal wavelength column, e.g. "994.0"
        try:
            float(column_name)
            wavelength_columns.append(column)
            continue
        except (ValueError, TypeError):
            pass

        # Handle pandas-renamed duplicate wavelength columns.
        # Example:
        #   "994.0.1"  -> original wavelength "994.0"
        #   "1009.3.1" -> original wavelength "1009.3"
        if "." in column_name:
            base_name, duplicate_suffix = column_name.rsplit(".", 1)

            if duplicate_suffix.isdigit():
                try:
                    float(base_name)
                    wavelength_columns.append(column)
                except (ValueError, TypeError):
                    pass

    return wavelength_columns


def prepare_spectral_data(df, wavelength_columns):
    """
    Convert wavelength readings to numeric values.

    Empty or invalid values become NaN and are ignored in the
    mean / SD calculations.
    """
    return df[wavelength_columns].apply(
        pd.to_numeric,
        errors="coerce",
    )


# ============================================================
# Mean and Standard Deviation
# ============================================================

def calculate_mean(spectral_data):
    """
    Calculate the mean independently for every wavelength.

    Missing values are ignored.
    """
    return spectral_data.mean(
        axis=0,
        skipna=True,
    )


def calculate_sd(
    spectral_data,
    ddof=DEFAULT_DDOF,
):
    """
    Calculate the standard deviation independently for every wavelength.

    Missing values are ignored.
    """
    return spectral_data.std(
        axis=0,
        skipna=True,
        ddof=ddof,
    )


def get_valid_wavelengths(
    spectral_data,
    wavelength_sds,
    min_valid_values=DEFAULT_MIN_VALID_VALUES,
):
    """
    Select wavelengths that are valid for SD-based outlier detection.

    A wavelength is used only when:
    - it has at least min_valid_values readings
    - its standard deviation is available
    - its standard deviation is greater than zero
    """
    valid_counts = spectral_data.count()

    valid_mask = (
        (valid_counts >= min_valid_values)
        & wavelength_sds.notna()
        & (wavelength_sds > 0)
    )

    return valid_counts.index[
        valid_mask
    ].tolist()


# ============================================================
# Z-score Calculation
# ============================================================

def calculate_z_scores(
    spectral_data,
    wavelength_means,
    wavelength_sds,
    valid_wavelengths,
):
    """
    Calculate Z-scores for all valid wavelength readings.

    Formula:
        Z = (value - mean) / standard_deviation
    """
    if not valid_wavelengths:
        return pd.DataFrame(
            index=spectral_data.index
        )

    valid_data = spectral_data[
        valid_wavelengths
    ]

    valid_means = wavelength_means[
        valid_wavelengths
    ]

    valid_sds = wavelength_sds[
        valid_wavelengths
    ]

    return valid_data.subtract(
        valid_means,
        axis="columns",
    ).divide(
        valid_sds,
        axis="columns",
    )


# ============================================================
# Outlier Output
# ============================================================

def build_outlier_output(
    df,
    z_scores,
    wavelength_columns,
    sd_threshold=DEFAULT_SD_THRESHOLD,
    id_column=DEFAULT_ID_COLUMN,
    group_by=DEFAULT_GROUP_BY,
    max_outliers=DEFAULT_MAX_OUTLIERS,
):
    """
    Create one output row per outlier file.

    A file is an outlier if ANY valid wavelength has:
        abs(Z-score) > sd_threshold

    Final output contains:
    - all original non-wavelength columns
    - OutlierPointCount
    - AverageAbsSD
    - MaxAbsSD

    Detailed wavelength-level calculations are used internally only
    and are not written to the CSV.
    """

    # Keep all original metadata/detail columns and remove wavelengths.
    metadata_columns = [
        column
        for column in df.columns
        if column not in wavelength_columns
    ]

    output_records = []

    for row_index in df.index:

        # Get all valid Z-scores for this file.
        row_z_scores = z_scores.loc[
            row_index
        ].dropna()

        # Keep only wavelengths that exceed the SD threshold.
        outlier_z_scores = row_z_scores[
            row_z_scores.abs() > sd_threshold
        ]

        # If this file has no outlier wavelength, skip it.
        if outlier_z_scores.empty:
            continue

        # Copy all non-wavelength metadata from the original merged CSV.
        record = df.loc[
            row_index,
            metadata_columns
        ].to_dict()

        # Number of wavelength points classified as outliers.
        record["OutlierPointCount"] = int(
            len(outlier_z_scores)
        )

        # Average absolute standard-deviation distance across
        # this file's outlier wavelength points.
        record["AverageAbsSD"] = float(
            outlier_z_scores.abs().mean()
        )

        # Strongest standard-deviation distance found in this file.
        record["MaxAbsSD"] = float(
            outlier_z_scores.abs().max()
        )

        output_records.append(record)

    calculation_columns = [
        "OutlierPointCount",
        "AverageAbsSD",
        "MaxAbsSD",
    ]

    # Return an empty output with the correct headers when
    # no files are classified as outliers.
    if not output_records:
        return pd.DataFrame(
            columns=metadata_columns + calculation_columns
        )

    outlier_df = pd.DataFrame(
        output_records
    )

    # FileNum should already be unique, but this avoids duplicate
    # rows if duplicate IDs somehow exist in the merged input.
    outlier_df = outlier_df.drop_duplicates(
        subset=[id_column]
    )

    # If grouping is requested, organise files under that group.
    if group_by is not None:

        if group_by not in outlier_df.columns:
            raise ValueError(
                f"Grouping column '{group_by}' "
                "was not found in the merged CSV."
            )

        outlier_df = outlier_df.sort_values(
            by=[
                group_by,
                "MaxAbsSD",
            ],
            ascending=[
                True,
                False,
            ],
            na_position="last",
        )

    else:
        # Without grouping, strongest outlier files appear first.
        outlier_df = outlier_df.sort_values(
            by="MaxAbsSD",
            ascending=False,
            na_position="last",
        )

    # Detection happens before limiting.
    # This controls only how many unique outlier files are written.
    if max_outliers is not None:
        outlier_df = outlier_df.head(
            max_outliers
        )

    return outlier_df.reset_index(
        drop=True
    )


def build_grouped_result(
    outlier_df,
    group_by=DEFAULT_GROUP_BY,
):
    """
    Build an optional grouped in-memory result.

    Example when group_by="Name":

        {
            "PlantA": [record1, record2],
            "PlantB": [record3]
        }

    The CSV itself remains a normal table and includes the grouping
    column as part of the metadata.
    """
    if group_by is None:
        return None

    grouped_result = {}

    for group_value, group_df in outlier_df.groupby(
        group_by,
        dropna=False,
    ):
        grouped_result[
            str(group_value)
        ] = group_df.to_dict(
            orient="records"
        )

    return grouped_result


# ============================================================
# Public Entry Point
# ============================================================

def main(
    input_path,
    output_path=None,
    sd_threshold=DEFAULT_SD_THRESHOLD,
    max_outliers=DEFAULT_MAX_OUTLIERS,
    id_column=DEFAULT_ID_COLUMN,
    group_by=DEFAULT_GROUP_BY,
    min_valid_values=DEFAULT_MIN_VALID_VALUES,
    ddof=DEFAULT_DDOF,
):
    """
    Run Hyperkey outlier analysis.

    Output:
    - one row per outlier file
    - all non-wavelength columns from merged spectral data
    - OutlierPointCount
    - AverageAbsSD
    - MaxAbsSD

    Detailed wavelength-level mean / SD / Z-score calculations are
    performed internally only.
    """

    input_path = Path(
        input_path
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input CSV does not exist: {input_path}"
        )

    # Validate settings.
    if sd_threshold <= 0:
        raise ValueError(
            "sd_threshold must be greater than 0."
        )

    if (
        max_outliers is not None
        and max_outliers < 1
    ):
        raise ValueError(
            "max_outliers must be at least 1 or None."
        )

    if min_valid_values < 2:
        raise ValueError(
            "min_valid_values must be at least 2."
        )

    if ddof < 0:
        raise ValueError(
            "ddof cannot be negative."
        )

    # Build output path.
    if output_path is None:

        output_path = input_path.with_name(
            f"{input_path.stem}_outlier_analysis.csv"
        )

    else:

        output_path = Path(
            output_path
        )

        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(
                ".csv"
            )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Load merged spectral CSV.
    df = pd.read_csv(
        input_path,
        dtype={
            id_column: "string"
        },
    )

    if id_column not in df.columns:
        raise ValueError(
            f"ID column '{id_column}' "
            "was not found in the merged CSV."
        )

    if (
        group_by is not None
        and group_by not in df.columns
    ):
        raise ValueError(
            f"Grouping column '{group_by}' "
            "was not found in the merged CSV."
        )

    # Identify spectral columns.
    wavelength_columns = identify_wavelength_columns(
        df
    )

    if not wavelength_columns:
        raise ValueError(
            "No numeric wavelength columns "
            "were found in the merged CSV."
        )

    # Prepare spectral readings.
    spectral_data = prepare_spectral_data(
        df=df,
        wavelength_columns=wavelength_columns,
    )

    # Calculate wavelength means.
    wavelength_means = calculate_mean(
        spectral_data=spectral_data,
    )

    # Calculate wavelength standard deviations.
    wavelength_sds = calculate_sd(
        spectral_data=spectral_data,
        ddof=ddof,
    )

    # Determine wavelengths that are valid for analysis.
    valid_wavelengths = get_valid_wavelengths(
        spectral_data=spectral_data,
        wavelength_sds=wavelength_sds,
        min_valid_values=min_valid_values,
    )

    # Calculate Z-scores.
    z_scores = calculate_z_scores(
        spectral_data=spectral_data,
        wavelength_means=wavelength_means,
        wavelength_sds=wavelength_sds,
        valid_wavelengths=valid_wavelengths,
    )

    # Build one row per outlier file.
    outlier_df = build_outlier_output(
        df=df,
        z_scores=z_scores,
        wavelength_columns=wavelength_columns,
        sd_threshold=sd_threshold,
        id_column=id_column,
        group_by=group_by,
        max_outliers=max_outliers,
    )

    # Save result.
    outlier_df.to_csv(
        output_path,
        index=False,
    )

    # Build optional grouped result.
    grouped_result = build_grouped_result(
        outlier_df=outlier_df,
        group_by=group_by,
    )

    # Terminal output.
    print(
        f"Outlier files written: {len(outlier_df)}"
    )

    print(
        f"Outlier output saved: {output_path}"
    )

    # Keep the return object compact so report/PDF generation does not
    # receive unnecessary wavelength-level statistics.
    return {
        "output_path": str(
            output_path
        ),
        "outlier_file_count": int(
            len(outlier_df)
        ),
        "group_by": group_by,
        "grouped_result": grouped_result,
    }


if __name__ == "__main__":
    raise SystemExit(
        "Run outlier analysis through "
        "hyperkey.py/workflow.py, or import "
        "outlier_analysis.main(...) from another module."
    )
