# HyperKey Sample Dataset 1

This sample is subsampled from an actual field campaign. Hopefully I (Ming) haven't messed up the subsampling ...

`sample-field-metadata.csv` describes additional metadata about the experimental plant growth unit, which in this case is a plot defined by a unique Row and Range (X and Y axes for most agricultural research fields)

`sample-sampling-metadata.csv` describes how we record samples in a field, which can differ from the instrument's numbering system. This is especially true if an obvious mistake is made and we can't delete files from the instrument so we skip the number and record the next. The WR column indicates files used for the white reference measurement, which in this case is File 0 (`Day1/HR.090323.0000.sig`)
This metadata file is technically optional to HyperKey's core functions but very useful to have combined with the "core" metadata, if available.

`Day1` is a folder containing the actual SVC `.sig` raw data files. The naming convention is `<manually set prefix>.<MMDDYY>.<4 digit sequential number>.sig`. Yes, this instrument was made in the US, hence the date system; no, we can't change it.

`sample-combined-file.csv` unifies the two main metadata sheets + hyperspec measurements into one single sheet with sampling metadata, plant unit metadata, and hyperspectral data.
