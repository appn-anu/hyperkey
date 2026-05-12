# Modular ExtractPro

This is the modular version of `extractPro.py`. The original single-file script has been split into a small package while keeping the same main behaviour.

## File structure

```text
modular_extract_pro/
├── extractPro.py                  # Thin entry point
└── spectral_merge/
    ├── __init__.py
    ├── cli.py                     # Argument parsing and workflow orchestration
    ├── config.py                  # Dataclasses and timestamp helper
    ├── metadata.py                # Metadata CSV reading and interactive selection
    ├── paths.py                   # Project path and .sig path building
    ├── processor.py               # Main merge logic
    ├── prompts.py                 # Interactive menu helper
    ├── sig_parser.py              # .sig file parsing
    ├── validators.py              # FileNum validation/formatting
    └── writers.py                 # CSV, log, summary JSON, terminal output
```

## How to run

From inside the `modular_extract_pro` folder:

```bash
python extractPro.py metadata.csv -r path/to/raw_data -o merged_spectral_data.csv
```

Or run without arguments to use the interactive prompts:

```bash
python extractPro.py
```

## Backward compatibility

The old `--config` option is still accepted as an alias for the root folder:

```bash
python extractPro.py metadata.csv --config path/to/raw_data
```

## Outputs

By default, outputs are written to:

```text
data/output_data/merged_spectral_data.csv
data/output_data/error_log.txt
data/output_data/summary.json
```
