from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

import flet as ft

from .components import browse_field, help_item, section_card, stat_card
from .models import HyperkeyRunConfig, RunResult
from .pipeline_service import PipelineService


class HyperkeyUI:
    def __init__(self, page: ft.Page, service: PipelineService | None = None):
        self.page = page
        self.service = service or PipelineService()
        self.current_screen = 0
        self.last_result: RunResult | None = None
        self._mounted = False

        self._configure_page()
        self._create_controls()
        self._build_shell()

    # ------------------------------------------------------------------
    # App setup
    # ------------------------------------------------------------------
    def _configure_page(self) -> None:
        self.page.title = "Hyperkey"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0

        # Keep the visual language simple and close to Material defaults so the
        # same code works comfortably on desktop and Android.
        self.page.theme = ft.Theme(use_material3=True)
        self.page.dark_theme = ft.Theme(use_material3=True)

    def _create_controls(self) -> None:
        # Normal form fields
        self.metadata_field = ft.TextField(
            label="Metadata CSV file(s)",
            hint_text="Enter one file path per line",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_change=self._refresh_command_preview,
        )
        self.root_field = ft.TextField(
            label="Raw spectral-data root folder",
            hint_text="Folder containing .sig files",
            on_change=self._refresh_command_preview,
        )
        self.location_field = ft.TextField(
            label="Species location file (optional)",
            hint_text="Path to location CSV",
            on_change=self._refresh_command_preview,
        )
        self.output_name_field = ft.TextField(
            label="Output name (optional)",
            hint_text="Example: sydneyAPPN",
            on_change=self._refresh_command_preview,
        )
        self.output_directory_field = ft.TextField(
            label="Output directory (optional)",
            hint_text="Where generated files should be saved",
            on_change=self._refresh_command_preview,
        )

        self.dark_mode_switch = ft.Switch(
            label="Dark visualisations",
            value=True,
            on_change=self._refresh_command_preview,
        )
        self.outlier_switch = ft.Switch(
            label="Outlier analysis",
            value=False,
            on_change=self._refresh_command_preview,
        )

        self.form_status = ft.Text()
        self.processing_bar = ft.ProgressBar(visible=False)
        self.command_preview = ft.TextField(
            label="Equivalent CLI command",
            read_only=True,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )

        # Advanced CLI fallback
        self.cli_field = ft.TextField(
            label="Hyperkey arguments or full command",
            hint_text=(
                'metadata.csv -r raw_data -o result  OR  '
                'python hyperkey.py metadata.csv -r raw_data'
            ),
            multiline=True,
            min_lines=5,
            max_lines=9,
        )
        self.cli_status = ft.Text()

        self.run_button = ft.Button(
            content="Run Hyperkey",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._run_form,
        )
        self.cli_run_button = ft.Button(
            content="Run arguments",
            icon=ft.Icons.TERMINAL,
            on_click=self._run_cli,
        )

        # Results / outputs / log controls
        self.results_content = ft.Column(spacing=12)

        # Outputs are intentionally separate from Results. Results remains the
        # run-statistics screen; Outputs is for generated files and report preview.
        self.outputs_content = ft.Column(spacing=12)
        self.output_status = ft.Text()
        self.url_launcher = ft.UrlLauncher()

        self.logs_field = ft.TextField(
            label="Run log",
            multiline=True,
            read_only=True,
            min_lines=14,
            max_lines=24,
            value="No run has been started yet.",
        )

        self.content_host = ft.Container(expand=True)

        self.theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE_OUTLINED,
            tooltip="Toggle app theme",
            on_click=self._toggle_app_theme,
        )
        self.help_button = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip="Help",
            on_click=self._show_help,
        )

        self.navigation = ft.NavigationBar(
            selected_index=0,
            on_change=self._change_screen,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                    selected_icon=ft.Icons.PLAY_CIRCLE,
                    label="Run",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.TERMINAL_OUTLINED,
                    selected_icon=ft.Icons.TERMINAL,
                    label="CLI",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS,
                    label="Results",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.FOLDER_COPY_OUTLINED,
                    selected_icon=ft.Icons.FOLDER_COPY,
                    label="Outputs",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    selected_icon=ft.Icons.RECEIPT_LONG,
                    label="Logs",
                ),
            ],
        )

        self._refresh_command_preview(None)

    def _build_shell(self) -> None:
        header = ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("HYPERKEY", theme_style=ft.TextThemeStyle.TITLE_LARGE),
                            ft.Text(
                                "Hyperspectral data processing",
                                theme_style=ft.TextThemeStyle.BODY_SMALL,
                            ),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    self.help_button,
                    self.theme_button,
                ],
            ),
        )

        self.page.navigation_bar = self.navigation
        self.page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[header, ft.Divider(height=1), self.content_host],
                ),
            )
        )

        # Controls can only be updated individually after they are mounted.
        self._mounted = True
        self._render_screen()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _metadata_paths(self) -> list[str]:
        return [line.strip() for line in (self.metadata_field.value or "").splitlines() if line.strip()]

    def _config_from_form(self) -> HyperkeyRunConfig:
        return HyperkeyRunConfig(
            metadata_files=self._metadata_paths(),
            root_folder=(self.root_field.value or "").strip(),
            raw_location_path=(self.location_field.value or "").strip(),
            output_name=(self.output_name_field.value or "").strip(),
            output_directory=(self.output_directory_field.value or "").strip(),
            dark_mode=bool(self.dark_mode_switch.value),
            outlier_analysis=bool(self.outlier_switch.value),
        )

    async def _portable_file_path(self, picked: ft.FilePickerFile) -> str:
        """
        Return a usable path for desktop or Android.

        Native pickers normally expose .path. Some mobile picker providers may
        not. Because we request with_data=True, bytes are available as a fallback
        and are copied into Flet's writable temporary app storage.
        """
        if picked.path:
            return picked.path

        if picked.bytes is None:
            return picked.name

        base = os.getenv("FLET_APP_STORAGE_TEMP") or tempfile.gettempdir()
        temp_dir = Path(base) / "hyperkey" / "picked_inputs"
        temp_dir.mkdir(parents=True, exist_ok=True)
        destination = temp_dir / f"{uuid4().hex}_{picked.name}"
        destination.write_bytes(picked.bytes)
        return str(destination)

    # ------------------------------------------------------------------
    # Pickers
    # ------------------------------------------------------------------
    async def _pick_metadata(self, _e) -> None:
        files = await ft.FilePicker().pick_files(
            dialog_title="Select metadata CSV files",
            allow_multiple=True,
            with_data=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
        )
        if not files:
            return

        paths = [await self._portable_file_path(file) for file in files]
        self.metadata_field.value = "\n".join(paths)
        self._refresh_command_preview(None)

    async def _pick_location(self, _e) -> None:
        files = await ft.FilePicker().pick_files(
            dialog_title="Select species location file",
            allow_multiple=False,
            with_data=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
        )
        if not files:
            return

        self.location_field.value = await self._portable_file_path(files[0])
        self._refresh_command_preview(None)

    async def _pick_root_folder(self, _e) -> None:
        path = await ft.FilePicker().get_directory_path(dialog_title="Select raw spectral-data folder")
        if path:
            self.root_field.value = path
            self._refresh_command_preview(None)

    async def _pick_output_folder(self, _e) -> None:
        path = await ft.FilePicker().get_directory_path(dialog_title="Select output folder")
        if path:
            self.output_directory_field.value = path
            self._refresh_command_preview(None)

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------
    def _run_screen(self) -> ft.Control:
        input_card = section_card(
            "Input data",
            subtitle="Type paths directly or use Browse.",
            controls=[
                browse_field(
                    self.metadata_field,
                    self._pick_metadata,
                    button_text="Browse CSV",
                    button_icon=ft.Icons.UPLOAD_FILE,
                ),
                browse_field(self.root_field, self._pick_root_folder, button_text="Browse folder"),
                browse_field(
                    self.location_field,
                    self._pick_location,
                    button_text="Browse CSV",
                    button_icon=ft.Icons.UPLOAD_FILE,
                ),
            ],
        )

        output_card = section_card(
            "Output",
            subtitle="Leave optional values blank to keep backend defaults.",
            controls=[
                self.output_name_field,
                browse_field(self.output_directory_field, self._pick_output_folder, button_text="Browse folder"),
            ],
        )

        options_card = section_card(
            "Analysis options",
            controls=[
                self.dark_mode_switch,
                self.outlier_switch,
            ],
        )

        command_card = section_card(
            "Command preview",
            subtitle="This is the equivalent hyperkey.py CLI command.",
            controls=[self.command_preview],
        )

        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("Run Hyperkey", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                    ft.Text("Configure a processing job using the simple form below."),
                    input_card,
                    output_card,
                    options_card,
                    command_card,
                    self.processing_bar,
                    self.form_status,
                    self.run_button,
                    ft.Container(height=12),
                ],
            ),
        )

    def _cli_screen(self) -> ft.Control:
        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("Advanced argument mode", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                    ft.Text(
                        "Failsafe mode. Paste arguments only or a complete 'python hyperkey.py ...' command."
                    ),
                    section_card(
                        "CLI input",
                        controls=[
                            self.cli_field,
                            ft.Text(
                                "Example: metadata.csv -r raw_data -o sydneyAPPN "
                                "-l species_locations.csv --outlier-analysis",
                                theme_style=ft.TextThemeStyle.BODY_SMALL,
                            ),
                        ],
                    ),
                    self.cli_status,
                    self.cli_run_button,
                ],
            ),
        )

    def _results_screen(self) -> ft.Control:
        self._render_results_content()
        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("Results", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                    self.results_content,
                ],
            ),
        )


    def _output_directory(self) -> Path | None:
        """Return the output directory for the most recent successful run."""
        if self.last_result is None or not self.last_result.summary:
            return None

        value = self.last_result.summary.get("output_directory")
        if not value:
            return None

        try:
            return Path(str(value)).expanduser()
        except Exception:
            return None

    @staticmethod
    def _resolve_generated_path(value) -> Path | None:
        """
        Resolve an output path returned by the backend.

        Visualisation modules sometimes receive an output base without a file
        extension and append their own extension. If the exact path does not
        exist, look for a file with the same base name and any extension.
        """
        if not value:
            return None

        candidate = Path(str(value)).expanduser()

        if candidate.exists() and candidate.is_file():
            return candidate

        parent = candidate.parent
        if not parent.exists():
            return None

        matches = sorted(
            (path for path in parent.glob(candidate.name + ".*") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return matches[0] if matches else None

    def _generated_output_files(self) -> list[tuple[str, Path]]:
        """
        Return the core generated files from the latest run.

        This deliberately uses backend result fields instead of listing every
        file in output_data, so files from older runs are not mixed into the
        current Outputs screen.
        """
        if self.last_result is None or not self.last_result.summary:
            return []

        summary = self.last_result.summary
        requested = [
            ("Merged spectral data", summary.get("output_csv")),
            ("Heatmap", summary.get("heatmap_output")),
            ("Spectral graph", summary.get("spectral_graph_output")),
        ]

        # Show outlier output too whenever that stage generated a file.
        outlier = summary.get("outlier_output")
        if outlier:
            requested.append(("Outlier analysis", outlier))

        files: list[tuple[str, Path]] = []
        seen: set[str] = set()

        for label, value in requested:
            path = self._resolve_generated_path(value)
            if path is None:
                continue

            key = str(path.resolve())
            if key in seen:
                continue

            seen.add(key)
            files.append((label, path))

        return files

    def _markdown_report_path(self) -> Path | None:
        """
        Find the Markdown report generated for the latest run.

        Markdown is used for the in-app preview because Flet has a native
        Markdown control, while PDF/HTML require a separate viewer/web view.
        """
        output_directory = self._output_directory()
        if output_directory is None or not output_directory.exists():
            return None

        candidates = [
            path
            for path in output_directory.rglob("*.md")
            if path.is_file() and "report" in path.name.lower()
        ]

        if not candidates:
            candidates = [
                path for path in output_directory.rglob("*.md") if path.is_file()
            ]

        if not candidates:
            return None

        return max(candidates, key=lambda path: path.stat().st_mtime)

    async def _open_output_path(self, path: Path) -> None:
        """
        Open an output using the operating system while keeping Hyperkey open.

        Desktop opens the file in its associated application. On Android the
        platform launcher chooses the associated viewer when available.
        """
        try:
            resolved = path.resolve()
            await self.url_launcher.launch_url(
                resolved.as_uri(),
                mode=ft.LaunchMode.EXTERNAL_APPLICATION,
            )
            self.output_status.value = f"Opened: {resolved.name}"
        except Exception as exc:
            self.output_status.value = (
                f"Unable to open '{path.name}' automatically: {exc}"
            )

        self.page.update()

    def _output_file_card(self, label: str, path: Path) -> ft.Card:
        async def open_file(_e) -> None:
            await self._open_output_path(path)

        size_text = ""
        try:
            size = path.stat().st_size
            if size < 1024:
                size_text = f"{size} B"
            elif size < 1024 * 1024:
                size_text = f"{size / 1024:.1f} KB"
            else:
                size_text = f"{size / (1024 * 1024):.1f} MB"
        except Exception:
            pass

        subtitle = str(path)
        if size_text:
            subtitle += f"\n{size_text}"

        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
                title=ft.Text(label, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(subtitle, max_lines=3),
                trailing=ft.Icon(ft.Icons.OPEN_IN_NEW),
                on_click=open_file,
            )
        )


    def _markdown_report_controls(
        self,
        markdown_text: str,
        report_path: Path,
    ) -> list[ft.Control]:
        """
        Render the generated Markdown report using ordinary Flet controls.

        We intentionally avoid ft.Markdown here. On some desktop Flet builds,
        the Markdown renderer can reserve a very large vertical surface even
        when fit_content=True. Using Text/Image controls keeps the report height
        equal to its actual content and also gives reliable local-image support.

        Supported report elements:
          - #, ##, ###, #### headings
          - normal paragraphs
          - unordered and ordered list items
          - horizontal rules
          - local Markdown images
          - simple Markdown tables (displayed as compact monospace text)
        """
        controls: list[ft.Control] = []

        image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        lines = markdown_text.splitlines()

        paragraph_lines: list[str] = []
        table_lines: list[str] = []

        def flush_paragraph() -> None:
            if not paragraph_lines:
                return

            value = " ".join(
                line.strip()
                for line in paragraph_lines
                if line.strip()
            ).strip()

            paragraph_lines.clear()

            if value:
                controls.append(
                    ft.Text(
                        value,
                        selectable=True,
                        size=14,
                    )
                )

        def flush_table() -> None:
            if not table_lines:
                return

            # Keep Markdown tables compact and readable without invoking the
            # Markdown/WebView renderer that caused the oversized blank area.
            cleaned = []
            for line in table_lines:
                stripped = line.strip()
                if re.fullmatch(r"\|?[\s:\-\|]+\|?", stripped):
                    continue
                cleaned.append(stripped)

            table_lines.clear()

            if cleaned:
                controls.append(
                    ft.Container(
                        padding=10,
                        border=ft.Border.all(1),
                        border_radius=8,
                        content=ft.Text(
                            "\n".join(cleaned),
                            selectable=True,
                            font_family="monospace",
                            size=12,
                        ),
                    )
                )

        def add_image(alt_text: str, image_reference: str) -> None:
            image_reference = image_reference.strip().strip("<>")

            if image_reference.lower().startswith(
                ("http://", "https://", "data:")
            ):
                controls.append(
                    ft.Text(
                        f"{alt_text or 'Image'}: {image_reference}",
                        selectable=True,
                    )
                )
                return

            image_path = Path(image_reference)

            if not image_path.is_absolute():
                image_path = report_path.parent / image_path

            try:
                image_path = image_path.resolve()
            except Exception:
                pass

            if not image_path.exists() or not image_path.is_file():
                controls.append(
                    ft.Text(
                        f"Image not found: {image_reference}",
                        selectable=True,
                    )
                )
                return

            try:
                image_bytes = image_path.read_bytes()

                controls.append(
                    ft.Container(
                        padding=ft.Padding.only(top=6, bottom=14),
                        content=ft.Column(
                            spacing=6,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Image(
                                    src=image_bytes,
                                    fit=ft.BoxFit.CONTAIN,
                                ),
                                ft.Text(
                                    alt_text,
                                    theme_style=ft.TextThemeStyle.BODY_SMALL,
                                    text_align=ft.TextAlign.CENTER,
                                    visible=bool(alt_text),
                                ),
                            ],
                        ),
                    )
                )
            except Exception as exc:
                controls.append(
                    ft.Text(
                        f"Unable to load image '{image_reference}': {exc}",
                        selectable=True,
                    )
                )

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()

            # Blank line ends paragraph/table blocks.
            if not stripped:
                flush_paragraph()
                flush_table()
                continue

            image_match = image_pattern.fullmatch(stripped)
            if image_match:
                flush_paragraph()
                flush_table()
                add_image(
                    image_match.group(1).strip(),
                    image_match.group(2).strip(),
                )
                continue

            # Markdown tables.
            if stripped.startswith("|") and "|" in stripped[1:]:
                flush_paragraph()
                table_lines.append(stripped)
                continue
            else:
                flush_table()

            # Headings.
            heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
            if heading_match:
                flush_paragraph()

                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                heading_sizes = {
                    1: 28,
                    2: 23,
                    3: 19,
                    4: 16,
                }

                controls.append(
                    ft.Container(
                        padding=ft.Padding.only(
                            top=12 if level <= 2 else 8,
                            bottom=4,
                        ),
                        content=ft.Text(
                            heading_text,
                            selectable=True,
                            size=heading_sizes[level],
                            weight=ft.FontWeight.BOLD,
                        ),
                    )
                )
                continue

            # Horizontal rule.
            if re.fullmatch(r"[-*_]{3,}", stripped):
                flush_paragraph()
                controls.append(ft.Divider())
                continue

            # Unordered list.
            unordered = re.match(r"^[-*+]\s+(.+)$", stripped)
            if unordered:
                flush_paragraph()
                controls.append(
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        spacing=8,
                        controls=[
                            ft.Text("•"),
                            ft.Text(
                                unordered.group(1).strip(),
                                selectable=True,
                                expand=True,
                            ),
                        ],
                    )
                )
                continue

            # Ordered list.
            ordered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if ordered:
                flush_paragraph()
                controls.append(
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        spacing=8,
                        controls=[
                            ft.Text(f"{ordered.group(1)}."),
                            ft.Text(
                                ordered.group(2).strip(),
                                selectable=True,
                                expand=True,
                            ),
                        ],
                    )
                )
                continue

            # All remaining lines are collected into a normal paragraph.
            paragraph_lines.append(stripped)

        flush_paragraph()
        flush_table()

        if not controls:
            controls.append(ft.Text("The report is empty."))

        return controls

    def _outputs_screen(self) -> ft.Control:
        self._render_outputs_content()

        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("Outputs", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                    ft.Text(
                        "Generated files from the latest Hyperkey run. "
                        "Tap a file to open it without closing Hyperkey.",
                        theme_style=ft.TextThemeStyle.BODY_SMALL,
                    ),
                    self.output_status,
                    self.outputs_content,
                ],
            ),
        )

    def _render_outputs_content(self) -> None:
        self.outputs_content.controls.clear()

        if self.last_result is None:
            self.outputs_content.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Text("No Hyperkey run has been started yet."),
                    )
                )
            )
            return

        if not self.last_result.success:
            self.outputs_content.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Text(
                            "The latest run did not complete successfully, "
                            "so generated outputs are not available."
                        ),
                    )
                )
            )
            return

        generated_files = self._generated_output_files()

        if generated_files:
            self.outputs_content.controls.append(
                section_card(
                    "Generated files",
                    subtitle="Tap any file to open it in the default application.",
                    controls=[
                        self._output_file_card(label, path)
                        for label, path in generated_files
                    ],
                )
            )
        else:
            self.outputs_content.controls.append(
                section_card(
                    "Generated files",
                    controls=[
                        ft.Text(
                            "No generated output files could be resolved from "
                            "the latest backend result."
                        )
                    ],
                )
            )

        report_path = self._markdown_report_path()

        if report_path is None:
            self.outputs_content.controls.append(
                section_card(
                    "Report preview",
                    subtitle="Markdown is the native in-app report format used by Hyperkey.",
                    controls=[
                        ft.Text(
                            "No Markdown report was found in the current output directory."
                        )
                    ],
                )
            )
            return

        try:
            markdown_text = report_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:
            self.outputs_content.controls.append(
                section_card(
                    "Report preview",
                    controls=[ft.Text(f"Unable to read report: {exc}")],
                )
            )
            return

        async def open_report(_e) -> None:
            await self._open_output_path(report_path)

        self.outputs_content.controls.append(
            section_card(
                "Report preview",
                subtitle=(
                    f"{report_path.name} • Markdown is rendered directly inside Flet."
                ),
                controls=[
                    # ft.Row(
                    #     controls=[
                    #         ft.Text(str(report_path), expand=True, selectable=True),
                    #         ft.Button(
                    #             content="Open report",
                    #             icon=ft.Icons.OPEN_IN_NEW,
                    #             on_click=open_report,
                    #         ),
                    #     ],
                    #     wrap=True,
                    # ),
                    ft.Container(
                        padding=12,
                        content=ft.Column(
                            spacing=8,
                            controls=self._markdown_report_controls(
                                markdown_text,
                                report_path,
                            ),
                        ),
                    ),
                ],
            )
        )

    def _logs_screen(self) -> ft.Control:
        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text("Logs", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                    self.logs_field,
                ],
            ),
        )

    def _render_screen(self) -> None:
        screens = [
            self._run_screen,
            self._cli_screen,
            self._results_screen,
            self._outputs_screen,
            self._logs_screen,
        ]
        self.content_host.content = screens[self.current_screen]()
        self.page.update()

    def _render_results_content(self) -> None:
        self.results_content.controls.clear()

        if self.last_result is None:
            self.results_content.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Text("No Hyperkey run has been started yet."),
                    )
                )
            )
            return

        result = self.last_result
        status_text = "Ready / Success" if result.success else "Failed"
        argument_count = str(len(result.arguments))
        output_count = str(len(result.summary)) if result.summary else "0"

        self.results_content.controls.extend(
            [
                ft.ResponsiveRow(
                    controls=[
                        stat_card("Status", status_text, ft.Icons.CHECK_CIRCLE_OUTLINE if result.success else ft.Icons.ERROR_OUTLINE),
                        stat_card("Arguments", argument_count, ft.Icons.TERMINAL),
                        stat_card("Result fields", output_count, ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
                    ]
                ),
                section_card(
                    "Run summary",
                    controls=[
                        ft.Text(result.message),
                        ft.TextField(
                            label="Executed / prepared command",
                            read_only=True,
                            multiline=True,
                            value=self.service.format_command(result.arguments),
                        ),
                    ],
                ),
            ]
        )

        if result.summary:
            summary_lines = [f"{key}: {value}" for key, value in result.summary.items()]
            self.results_content.controls.append(
                section_card(
                    "Backend result",
                    controls=[ft.Text("\n".join(summary_lines), selectable=True)],
                )
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _change_screen(self, e) -> None:
        if e.control.selected_index is None:
            return
        self.current_screen = e.control.selected_index
        self._render_screen()

    def _refresh_command_preview(self, _e) -> None:
        config = self._config_from_form()
        args = self.service.build_arguments(config)
        self.command_preview.value = self.service.format_command(args)

        # During __init__, command_preview has not been mounted yet.
        # Updating the page only after _build_shell() prevents Flet's
        # "Control must be added to the page first" exception.
        if self._mounted:
            self.page.update()

    async def _run_form(self, _e) -> None:
        self.processing_bar.visible = True
        self.run_button.disabled = True
        self.form_status.value = "Running Hyperkey..."
        self.page.update()

        try:
            config = self._config_from_form()

            # Hyperkey's processing stack is synchronous and report generation
            # may use Playwright's Sync API. Run the complete backend in a worker
            # thread so it does not execute inside Flet's asyncio event loop.
            result = await asyncio.to_thread(
                self.service.run_config,
                config,
            )

        except Exception as exc:
            result = RunResult(
                False,
                f"Unable to start Hyperkey: {exc}",
                logs=[f"ERROR: {exc}"],
            )

        finally:
            self.processing_bar.visible = False
            self.run_button.disabled = False

        self._handle_result(result, self.form_status)

    async def _run_cli(self, _e) -> None:
        self.cli_run_button.disabled = True
        self.cli_status.value = "Running Hyperkey arguments..."
        self.page.update()

        try:
            arguments = self.service.parse_cli_text(self.cli_field.value or "")

            # Keep synchronous backend libraries, including Playwright Sync API,
            # outside Flet's asyncio event loop.
            result = await asyncio.to_thread(
                self.service.run_arguments,
                arguments,
            )

        except Exception as exc:
            result = RunResult(
                False,
                f"Invalid command/arguments: {exc}",
                logs=[f"ERROR: {exc}"],
            )

        finally:
            self.cli_run_button.disabled = False

        self._handle_result(result, self.cli_status)

    def _handle_result(self, result: RunResult, status_control: ft.Text) -> None:
        self.last_result = result
        status_control.value = result.message
        status_control.color = ft.Colors.GREEN if result.success else ft.Colors.RED
        self.logs_field.value = "\n".join(result.logs) if result.logs else result.message

        # Move to Results after a valid run. Invalid input stays on the current screen.
        if result.success:
            self.current_screen = 2
            self.navigation.selected_index = 2
            self._render_screen()
        else:
            self.page.update()

    def _toggle_app_theme(self, _e) -> None:
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_button.icon = ft.Icons.DARK_MODE_OUTLINED
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_button.icon = ft.Icons.LIGHT_MODE_OUTLINED
        self.page.update()

    def _show_help(self, _e) -> None:
        help_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Hyperkey help"),
            content=ft.Column(
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    help_item(
                        "Metadata CSV file(s)",
                        "Required. Enter one or more metadata CSV paths, one per line, or select them using Browse CSV.",
                    ),
                    help_item(
                        "Raw spectral-data root folder",
                        "Required. Folder that contains the .sig measurement files used by the metadata.",
                    ),
                    help_item(
                        "Species location file",
                        "Optional location CSV used by the heatmap/location workflow.",
                    ),
                    help_item(
                        "Output name",
                        "Optional base name. Existing Hyperkey dated naming is preserved by the backend.",
                    ),
                    help_item(
                        "Output directory",
                        "Optional destination directory for generated outputs. It is combined with Output name before being sent as -o.",
                    ),
                    help_item(
                        "App theme",
                        "The sun/moon button in the top-right changes only the Flet application's appearance.",
                    ),
                    help_item(
                        "Dark visualisations",
                        "Controls the colour mode of generated heatmaps, spectral graphs and reports. This is separate from the app's own theme button.",
                    ),
                    help_item(
                        "Outlier analysis",
                        "Runs the outlier-analysis stage when enabled.",
                    ),
                    help_item(
                        "Command preview",
                        "Shows the CLI command equivalent to the values entered in the normal form.",
                    ),
                    help_item(
                        "CLI mode",
                        "Failsafe/advanced mode. Enter only arguments or paste a complete python hyperkey.py command.",
                    ),
                    help_item(
                        "Outputs",
                        "Shows the files generated by the latest successful run. Tap a file to open it in the default application while Hyperkey remains open. The Markdown report is also previewed directly inside the app.",
                    ),
                    help_item(
                        "Results and Logs",
                        "Results shows the most recent run summary. Logs shows run messages and later will show the pipeline log output.",
                    ),
                ],
            ),
            actions=[ft.TextButton("Close", on_click=lambda _evt: self.page.pop_dialog())],
        )
        self.page.show_dialog(help_dialog)


def main(page: ft.Page) -> None:
    HyperkeyUI(page)


if __name__ == "__main__":
    ft.run(main)
