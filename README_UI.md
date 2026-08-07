# Hyperkey Flet UI - first pass

This folder contains only the new UI layer. It intentionally does not modify the existing pipeline yet.

## Intended locations in the Hyperkey repository

```text
hyperkey/
├── ui/
│   ├── __init__.py
│   ├── app.py
│   ├── components.py
│   ├── models.py
│   └── pipeline_service.py
├── run_ui.py                 # temporary UI-only development launcher
└── requirements-ui.txt       # merge into the main requirements later
```

The final public `hyperkey.py` entrypoint is deliberately not created in this UI-only pass. It should be added when the pipeline/CLI integration is updated.

## What is implemented

- One Flet UI shared by desktop and Android.
- Bottom navigation: Run, CLI, Results, Logs.
- Global Help dialog describing every input/option.
- Metadata CSV input supports multiple paths, one per line.
- All file/folder inputs support direct path entry plus Browse.
- Android-safe selected CSV handling: picker bytes are copied to writable temporary app storage when a normal path is unavailable.
- Optional output name and output directory.
- Dark visualisations toggle.
- Outlier analysis toggle.
- Equivalent `python hyperkey.py ...` command preview.
- Advanced CLI fallback accepts either arguments only or the complete command.
- Backend adapter (`PipelineService`) is intentionally disconnected until the pipeline integration pass.

## Development run

Install the UI dependency:

```bash
pip install -r requirements-ui.txt
```

Run:

```bash
python run_ui.py
```

or with Flet hot reload:

```bash
flet run run_ui.py
```

## Current backend behaviour

Clicking Run validates the inputs and prepares the exact argument list, then shows a result saying backend integration is pending. This is intentional for the UI-only pass.

During the next pipeline pass, `hyperkey.py` can create a `PipelineService(backend_runner=...)` so both the normal form and CLI screen invoke the same backend function.
