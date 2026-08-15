from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

import flet as ft

from .backend import import_app_paths
from .components import browse_field, help_item, section_card, stat_card
from .models import HyperkeyRunConfig, RunResult
from .pipeline_service import PipelineService

# Shared with the pipeline, so the UI and the backend agree on where output
# goes and on whether this is an Android build.
app_paths = import_app_paths()

# flet_permission_handler is only needed on Android, and is not installed in
# every desktop environment. Import it defensively so desktop never breaks.
try:
    import flet_permission_handler as fph
except ImportError:
    fph = None


class HyperkeyUI:
    # The theme button cycles through these in order. SYSTEM is first, and so
    # is the startup state: the app follows the phone's own light/dark setting
    # unless the user deliberately pins it. Keeping an explicit Light and Dark
    # in the cycle means "follow system" is a choice rather than a trap.
    THEME_CYCLE = (
        (ft.ThemeMode.SYSTEM, ft.Icons.BRIGHTNESS_AUTO, "App theme: follow system"),
        (ft.ThemeMode.LIGHT, ft.Icons.LIGHT_MODE_OUTLINED, "App theme: light"),
        (ft.ThemeMode.DARK, ft.Icons.DARK_MODE_OUTLINED, "App theme: dark"),
    )

    def __init__(self, page: ft.Page, service: PipelineService | None = None):
        self.page = page
        self.service = service or PipelineService()
        self.current_screen = 0
        self.last_result: RunResult | None = None
        self._mounted = False
        self._theme_index = 0

        self._configure_page()
        self._create_controls()
        self._build_shell()

    # ------------------------------------------------------------------
    # App setup
    # ------------------------------------------------------------------
    def _configure_page(self) -> None:
        self.page.title = "Hyperkey"
        self.page.theme_mode = self.THEME_CYCLE[0][0]
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

        if app_paths.is_android():
            # Android app storage is private and its path is not something a
            # user could reasonably type, so prefill it.
            self.output_directory_field.value = str(app_paths.default_output_directory())

        self.dark_mode_switch = ft.Switch(
            label="Dark visualisations",
            value=True,
            on_change=self._refresh_command_preview,
        )
        # The outlier-analysis toggle is hidden until scripts/outlier_analysis.py
        # lands. The switch object is kept so _config_from_form() and the CLI
        # preview keep working unchanged; it is simply never shown.
        self.outlier_switch = ft.Switch(
            label="Outlier analysis",
            value=False,
            visible=False,
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

        # Android cannot open file:// URIs (FileUriExposedException), so
        # generated files are handed to the system share sheet instead.
        self.share = ft.Share()
        self.permissions = (
            fph.PermissionHandler() if (fph is not None and app_paths.is_android()) else None
        )

        self.logs_field = ft.TextField(
            label="Run log",
            multiline=True,
            read_only=True,
            min_lines=14,
            max_lines=24,
            value="No run has been started yet.",
        )

        self.content_host = ft.Container(expand=True)

        _, theme_icon, theme_tooltip = self.THEME_CYCLE[self._theme_index]
        self.theme_button = ft.IconButton(
            icon=theme_icon,
            tooltip=theme_tooltip,
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
                    label="Home-Run",
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

    async def _ensure_storage_permission(self) -> bool:
        """
        Make sure we can read arbitrary folders before opening a directory picker.

        Only relevant on Android. Reading a user-chosen folder full of .sig
        files needs all-files access; Android routes that through Settings
        rather than a normal permission dialog, so the user needs telling.
        Returns True when browsing can proceed.
        """
        if not app_paths.is_android() or self.permissions is None:
            return True

        permission = fph.Permission.MANAGE_EXTERNAL_STORAGE

        status = await self.permissions.get_status(permission)

        if status != fph.PermissionStatus.GRANTED:
            status = await self.permissions.request(permission)

        if status == fph.PermissionStatus.GRANTED:
            return True

        async def open_settings(_e) -> None:
            self.page.pop_dialog()
            await self.permissions.open_app_settings()

        def dismiss(_e) -> None:
            self.page.pop_dialog()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Storage access needed"),
                content=ft.Text(
                    "Hyperkey needs all-files access to read a folder of .sig "
                    "measurements.\n\n"
                    "Grant it under Settings > Apps > Hyperkey > "
                    "Special app access > All files access."
                ),
                actions=[
                    ft.TextButton(content="Not now", on_click=dismiss),
                    ft.TextButton(content="Open settings", on_click=open_settings),
                ],
            )
        )

        return False

    async def _pick_root_folder(self, _e) -> None:
        if not await self._ensure_storage_permission():
            return

        path = await ft.FilePicker().get_directory_path(dialog_title="Select raw spectral-data folder")
        if path:
            self.root_field.value = path
            self._refresh_command_preview(None)

    async def _pick_output_folder(self, _e) -> None:
        if not await self._ensure_storage_permission():
            return

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
                                "-l species_locations.csv",
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
            ("Markdown report", summary.get("report_markdown_output")),
            ("Summary report", summary.get("summary_file")),
            ("Log file", summary.get("log_file")),
            ("Output directory", summary.get("output_directory")),
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
        Return the Markdown report path saved by the backend
        in summary["report_markdown_output"].
        """
        if self.last_result is None or not self.last_result.summary:
            return None

        value = self.last_result.summary.get("report_markdown_output")
        if not value:
            return None

        try:
            report_path = Path(str(value)).expanduser()

            if report_path.exists() and report_path.is_file():
                return report_path

        except Exception:
            pass

        return None

    async def _open_output_path(self, path: Path) -> None:
        """
        Hand an output file to the operating system, keeping Hyperkey open.

        Desktop opens the file in its associated application. Android blocks
        file:// URIs (FileUriExposedException), so there the file goes to the
        system share sheet, which also covers "save to Drive/Files".
        """
        try:
            resolved = path.resolve()

            if app_paths.is_android():
                await self.share.share_files(
                    [ft.ShareFile.from_path(str(resolved))],
                    subject=resolved.name,
                )
                self.output_status.value = f"Shared: {resolved.name}"
            else:
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

    def _show_fullscreen_image(self, image_bytes: bytes, caption: str = "") -> None:
        """
        Open a generated plot full screen, with pinch-zoom and pan.

        Zooming a plot where it sits in the report does not work: an
        InteractiveViewer inside a scrolling Column competes with the page for
        the same drag gestures, so a pan reads as a scroll about as often as it
        reads as a pan. Giving the image its own screen removes the conflict
        entirely, and as a dialog it also gets Android's back button for free.
        """
        # page.width / page.height are None until the first frame is measured.
        width = self.page.width or 400
        height = self.page.height or 700

        viewer = ft.InteractiveViewer(
            width=width,
            height=height,
            min_scale=1.0,
            max_scale=10.0,
            content=ft.Image(src=image_bytes, fit=ft.BoxFit.CONTAIN),
        )

        def close(_e) -> None:
            self.page.pop_dialog()

        async def reset_zoom(_e) -> None:
            # InteractiveViewer.reset() is a command sent to the Flutter side,
            # so it has to be awaited rather than fired and forgotten.
            await viewer.reset(animation_duration=200)

        overlay_button_bgcolor = ft.Colors.with_opacity(0.45, ft.Colors.BLACK)

        layers: list[ft.Control] = [
            viewer,
            ft.Container(
                top=8,
                right=8,
                content=ft.Row(
                    tight=True,
                    spacing=4,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.RESTART_ALT,
                            icon_color=ft.Colors.WHITE,
                            bgcolor=overlay_button_bgcolor,
                            tooltip="Reset zoom",
                            on_click=reset_zoom,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=ft.Colors.WHITE,
                            bgcolor=overlay_button_bgcolor,
                            tooltip="Close",
                            on_click=close,
                        ),
                    ],
                ),
            ),
        ]

        if caption:
            layers.append(
                ft.Container(
                    bottom=0,
                    left=0,
                    right=0,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
                    content=ft.Text(
                        caption,
                        color=ft.Colors.WHITE,
                        size=12,
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )

        self.page.show_dialog(
            ft.AlertDialog(
                # A borderless, edge-to-edge dialog on a black ground: the plots
                # are the whole point of the screen while this is open.
                bgcolor=ft.Colors.BLACK,
                barrier_color=ft.Colors.BLACK,
                inset_padding=ft.Padding.all(0),
                content_padding=ft.Padding.all(0),
                shape=ft.RoundedRectangleBorder(radius=0),
                content=ft.Stack(width=width, height=height, controls=layers),
            )
        )

    async def _export_output_path(self, path: Path) -> None:
        """
        Save an output file somewhere the user chooses.

        On Android this opens the Storage Access Framework dialog, which is
        the reliable way to get a merged CSV off the phone (Downloads, Drive,
        or anywhere else). save_file() requires the bytes up front on mobile.
        """
        try:
            saved = await ft.FilePicker().save_file(
                dialog_title=f"Save {path.name}",
                file_name=path.name,
                src_bytes=path.read_bytes(),
            )
            self.output_status.value = (
                f"Saved: {saved}" if saved else "Save cancelled."
            )

        except Exception as exc:
            self.output_status.value = f"Unable to save '{path.name}': {exc}"

        self.page.update()

    def _output_file_card(self, label: str, path: Path) -> ft.Card:
        async def open_file(_e) -> None:
            await self._open_output_path(path)

        async def save_file(_e) -> None:
            await self._export_output_path(path)

        is_image = path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}

        def view_image(_e) -> None:
            try:
                self._show_fullscreen_image(path.read_bytes(), label)
            except Exception as exc:
                self.output_status.value = f"Unable to view '{path.name}': {exc}"
                self.page.update()

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

        actions: list[ft.Control] = []

        if is_image:
            # Viewing a plot in-app should not require a detour through the
            # report, or through whatever gallery app the share sheet offers.
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.ZOOM_IN,
                    tooltip="View full screen",
                    on_click=view_image,
                )
            )

        actions.extend(
            [
                # Saving elsewhere matters most on Android, where app storage
                # is private and files need exporting to leave.
                ft.IconButton(
                    icon=ft.Icons.SAVE_ALT,
                    tooltip="Save a copy",
                    on_click=save_file,
                ),
                ft.Icon(
                    ft.Icons.SHARE if app_paths.is_android() else ft.Icons.OPEN_IN_NEW
                ),
            ]
        )

        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.IMAGE_OUTLINED
                    if is_image
                    else ft.Icons.INSERT_DRIVE_FILE_OUTLINED
                ),
                title=ft.Text(label, weight=ft.FontWeight.W_600),
                subtitle=ft.Text(subtitle, max_lines=3),
                trailing=ft.Row(tight=True, controls=actions),
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

                def open_fullscreen(_e, data=image_bytes, label=alt_text) -> None:
                    self._show_fullscreen_image(data, label or image_path.name)

                controls.append(
                    ft.Container(
                        padding=ft.Padding.only(top=6, bottom=14),
                        content=ft.Column(
                            spacing=6,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                # Plots are rendered at dpi=150 and are far
                                # wider than a phone screen, so the inline copy
                                # is only a preview. Tapping it opens the image
                                # full screen, where pinch-zoom has the display
                                # to itself instead of fighting the page scroll.
                                ft.Container(
                                    height=360,
                                    ink=True,
                                    border_radius=8,
                                    alignment=ft.Alignment.CENTER,
                                    tooltip="Tap to view full screen",
                                    on_click=open_fullscreen,
                                    content=ft.Image(
                                        src=image_bytes,
                                        fit=ft.BoxFit.CONTAIN,
                                    ),
                                ),
                                ft.Row(
                                    tight=True,
                                    spacing=4,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                                        ft.Icon(ft.Icons.ZOOM_IN, size=14),
                                        ft.Text(
                                            "Tap to view full screen",
                                            theme_style=ft.TextThemeStyle.BODY_SMALL,
                                        ),
                                    ],
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
                    ft.Row(
                        controls=[
                            # ft.Text(str(report_path), expand=False, selectable=False), 
                            # A long unwanted space issue, need fix later. Feature not requested by user, so commented out for now.
                            ft.Button(
                                content="Open report",
                                icon=ft.Icons.OPEN_IN_NEW,
                                on_click=open_report,
                            ),
                        ],
                        wrap=True,
                    ),
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
        """Step the app theme through system -> light -> dark -> system."""
        self._theme_index = (self._theme_index + 1) % len(self.THEME_CYCLE)

        mode, icon, tooltip = self.THEME_CYCLE[self._theme_index]

        self.page.theme_mode = mode
        self.theme_button.icon = icon
        self.theme_button.tooltip = tooltip
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
                        "The button in the top-right changes only the Hyperkey application's appearance. It cycles through follow-system, light and dark, and starts on follow-system.",
                    ),
                    help_item(
                        "Dark visualisations",
                        "Controls the colour mode of generated heatmaps, spectral graphs and reports. This is separate from the app's own theme button.",
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
                        "Viewing plots",
                        "Tap the heatmap or spectral graph, in the report preview or from its Outputs card, to open it full screen. Pinch to zoom and drag to pan there; the reset button restores the original fit.",
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
