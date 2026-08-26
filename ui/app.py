from __future__ import annotations

import asyncio
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

import flet as ft
import flet_permission_handler as fph

try:
    from hyperkey_file_opener import HyperkeyFileOpener
except ImportError:
    HyperkeyFileOpener = None

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

        # Follow the operating system's current light/dark preference by default.
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.padding = 0

        # Keep the visual language simple and close to Material defaults so the
        # same code works comfortably on desktop and Android.
        self.page.theme = ft.Theme(use_material3=True)
        self.page.dark_theme = ft.Theme(use_material3=True)

        # Keep Hyperkey in sync if the user changes the OS appearance while the
        # application is open.
        self.page.on_platform_brightness_change = self._on_platform_brightness_change

    def _style_input_field(self, field: ft.TextField) -> ft.TextField:
        """
        Give input/command fields a clearly visible outline on both Windows
        and Android while preserving responsive sizing.
        """
        field.border = ft.InputBorder.OUTLINE
        field.border_width = 2
        field.border_color = ft.Colors.GREY_600
        field.focused_border_width = 3
        field.focused_border_color = ft.Colors.BLUE_400
        field.border_radius = 10
        field.content_padding = ft.Padding.symmetric(horizontal=16, vertical=15)
        field.expand = True
        return field

    def _section_panel(
        self,
        title: str,
        *,
        subtitle: str | None = None,
        controls: list[ft.Control] | None = None,
        icon=None,
    ) -> ft.Control:
        """A clean Material-style section that works on desktop and mobile."""
        heading_controls: list[ft.Control] = []
        if icon is not None:
            heading_controls.append(ft.Icon(icon, size=20))

        heading_controls.append(
            ft.Column(
                spacing=1,
                expand=True,
                controls=[
                    ft.Text(title, weight=ft.FontWeight.W_600, size=16),
                    ft.Text(
                        subtitle or "",
                        theme_style=ft.TextThemeStyle.BODY_SMALL,
                        visible=bool(subtitle),
                    ),
                ],
            )
        )

        return ft.Card(
            elevation=1,
            content=ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                border=ft.Border.all(1, ft.Colors.GREY_700),
                border_radius=12,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=heading_controls,
                        ),
                        ft.Divider(height=1),
                        *(controls or []),
                    ],
                ),
            ),
        )

    def _responsive_browse_field(
        self,
        field: ft.TextField,
        picker,
        *,
        button_text: str,
        button_icon=ft.Icons.FOLDER_OPEN_OUTLINED,
    ) -> ft.Control:
        """
        Desktop: field and Browse button share one row.
        Android/small widths: Browse button moves below the field and becomes easy to tap.
        """
        browse_button = ft.Button(
            content=button_text,
            icon=button_icon,
            on_click=picker,
            height=48,
        )

        return ft.ResponsiveRow(
            spacing=10,
            run_spacing=8,
            controls=[
                ft.Container(
                    col={"xs": 12, "sm": 12, "md": 9, "lg": 10},
                    content=field,
                ),
                ft.Container(
                    col={"xs": 12, "sm": 12, "md": 3, "lg": 2},
                    content=browse_button,
                ),
            ],
        )

    def _responsive_switches(self) -> ft.Control:
        """Stack switches on phones and show them side-by-side on larger screens."""
        return ft.ResponsiveRow(
            spacing=12,
            run_spacing=8,
            controls=[
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                    border=ft.Border.all(1, ft.Colors.GREY_700),
                    border_radius=10,
                    content=self.dark_mode_switch,
                ),
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                    border=ft.Border.all(1, ft.Colors.GREY_700),
                    border_radius=10,
                    content=self.outlier_switch,
                ),
            ],
        )

    def _outlier_settings_panel(self) -> ft.Control:
        """Advanced outlier settings. Collapsed by default on desktop and mobile."""
        fields = [
            self.outlier_sd_threshold_field,
            self.outlier_max_outliers_field,
            self.outlier_id_column_field,
            self.outlier_group_by_field,
            self.outlier_min_valid_values_field,
            self.outlier_ddof_field,
        ]

        return ft.Container(
            border=ft.Border.all(1, ft.Colors.GREY_700),
            border_radius=10,
            content=ft.ExpansionTile(
                title=ft.Text("Outlier settings", weight=ft.FontWeight.W_600),
                subtitle=ft.Text(
                    "Optional overrides. Leave fields empty to use the stored defaults.",
                    theme_style=ft.TextThemeStyle.BODY_SMALL,
                ),
                expanded=False,
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(left=12, right=12, bottom=14),
                        content=ft.ResponsiveRow(
                            spacing=10,
                            run_spacing=10,
                            controls=[
                                ft.Container(
                                    col={"xs": 12, "sm": 6, "md": 4},
                                    content=field,
                                )
                                for field in fields
                            ],
                        ),
                    )
                ],
            ),
        )

    def _screen_title(self, title: str, subtitle: str) -> ft.Control:
        return ft.Column(
            spacing=3,
            controls=[
                ft.Text(title, theme_style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD),
                ft.Text(subtitle, theme_style=ft.TextThemeStyle.BODY_MEDIUM),
            ],
        )

    def _create_controls(self) -> None:
        # Normal form fields
        self.metadata_field = self._style_input_field(ft.TextField(
            label="Metadata CSV file(s)",
            hint_text="Enter one file path per line",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_change=self._refresh_command_preview,
        ))
        self.root_field = self._style_input_field(ft.TextField(
            label="Raw spectral-data root folder",
            hint_text="Folder containing .sig files",
            on_change=self._refresh_command_preview,
        ))
        self.location_field = self._style_input_field(ft.TextField(
            label="Species location file (optional)",
            hint_text="Path to location CSV",
            on_change=self._refresh_command_preview,
        ))
        self.output_name_field = self._style_input_field(ft.TextField(
            label="Output name (optional)",
            hint_text="Example: sydneyAPPN",
            on_change=self._refresh_command_preview,
        ))
        self.output_directory_field = self._style_input_field(ft.TextField(
            label="Output directory (optional)",
            hint_text="Default: Documents/Hyperkey (Windows), Downloads/Hyperkey (Android)",
            on_change=self._refresh_command_preview,
        ))

        self.dark_mode_switch = ft.Switch(
            label="Dark mode",
            value=self._system_is_dark(),
            on_change=self._on_dark_mode_switch_change,
        )
        self.outlier_switch = ft.Switch(
            label="Outlier analysis",
            value=False,
            on_change=self._refresh_command_preview,
        )

        # Optional UI-only outlier overrides. The fields intentionally start
        # empty: hint_text shows the stored backend default, while an empty
        # value means "do not override the workflow/outlier default".
        self.outlier_sd_threshold_field = self._style_input_field(ft.TextField(
            label="SD threshold",
            hint_text="Default: 2.0",
            keyboard_type=ft.KeyboardType.NUMBER,
        ))
        self.outlier_max_outliers_field = self._style_input_field(ft.TextField(
            label="Maximum outliers",
            hint_text="Default: 20 (or type None for all)",
        ))
        self.outlier_id_column_field = self._style_input_field(ft.TextField(
            label="ID column",
            hint_text="Default: FileNum",
        ))
        self.outlier_group_by_field = self._style_input_field(ft.TextField(
            label="Group by",
            hint_text="Default: None (e.g. Name, Genotype)",
        ))
        self.outlier_min_valid_values_field = self._style_input_field(ft.TextField(
            label="Minimum valid values",
            hint_text="Default: 10",
            keyboard_type=ft.KeyboardType.NUMBER,
        ))
        self.outlier_ddof_field = self._style_input_field(ft.TextField(
            label="DDOF",
            hint_text="Default: 1",
            keyboard_type=ft.KeyboardType.NUMBER,
        ))

        self.form_status = ft.Text()
        self.processing_bar = ft.ProgressBar(visible=False)
        self.command_preview = self._style_input_field(ft.TextField(
            label="Equivalent CLI command",
            read_only=True,
            multiline=True,
            min_lines=4,
            max_lines=8,
        ))
        self.copy_command_button = ft.IconButton(
            icon=ft.Icons.CONTENT_COPY,
            tooltip="Copy command",
            on_click=self._copy_command,
        )

        # Advanced CLI fallback. Keep this deliberately large because commands
        # can be long, especially when Android returns longer document paths.
        self.cli_field = self._style_input_field(ft.TextField(
            label="Hyperkey arguments or full command",
            hint_text=(
                'metadata.csv -r raw_data -n result  OR  '
                'metadata.csv -r raw_data -o output_folder -n result'
            ),
            multiline=True,
            min_lines=8,
            max_lines=14,
        ))
        self.cli_status = ft.Text()

        self.run_button = ft.Button(
            content="Run Hyperkey",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._run_form,
            height=52,
        )
        self.cli_run_button = ft.Button(
            content="Run arguments",
            icon=ft.Icons.TERMINAL,
            on_click=self._run_cli,
            height=52,
        )

        # Results / outputs / log controls
        self.results_content = ft.Column(spacing=12)

        # Outputs are intentionally separate from Results. Results remains the
        # run-statistics screen; Outputs is for generated files and report preview.
        self.outputs_content = ft.Column(spacing=12)
        self.output_status = ft.Text()
        self.url_launcher = ft.UrlLauncher()
        self.share_service = ft.Share()
        self.android_file_opener = (
            HyperkeyFileOpener() if HyperkeyFileOpener is not None else None
        )
        self.permission_handler = fph.PermissionHandler()

        self.logs_field = self._style_input_field(ft.TextField(
            label="Run log",
            multiline=True,
            read_only=True,
            min_lines=14,
            max_lines=24,
            value="No run has been started yet.",
        ))

        self.content_host = ft.Container(expand=True)

        self.theme_button = ft.IconButton(
            icon=(
                ft.Icons.LIGHT_MODE_OUTLINED
                if self._system_is_dark()
                else ft.Icons.DARK_MODE_OUTLINED
            ),
            tooltip="Toggle Hyperkey dark mode",
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
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Image(
                        src="hyperkey-logo-full.png",
                        height=46,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    ft.Column(
                        spacing=0,
                        expand=True,
                        controls=[
                            ft.Text("Hyperkey", weight=ft.FontWeight.BOLD, size=17),
                            ft.Text(
                                "Hyperspectral data processing",
                                theme_style=ft.TextThemeStyle.BODY_SMALL,
                            ),
                        ],
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
            outlier_sd_threshold=(self.outlier_sd_threshold_field.value or "").strip(),
            outlier_max_outliers=(self.outlier_max_outliers_field.value or "").strip(),
            outlier_id_column=(self.outlier_id_column_field.value or "").strip(),
            outlier_group_by=(self.outlier_group_by_field.value or "").strip(),
            outlier_min_valid_values=(self.outlier_min_valid_values_field.value or "").strip(),
            outlier_ddof=(self.outlier_ddof_field.value or "").strip(),
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

    def _is_android(self) -> bool:
        """Return True when Hyperkey is running as an Android app."""
        return self.page.platform == ft.PagePlatform.ANDROID

    async def _get_android_default_output_directory(self) -> Path:
        """
        Return Hyperkey's public Android output directory.

        Android uses the device Downloads directory so generated CSV, HTML,
        PDF, PNG, JSON, and log files remain user-visible and can be handed
        to compatible external applications.
        """
        downloads = await ft.StoragePaths().get_downloads_directory()

        if not downloads:
            raise RuntimeError(
                "Android Downloads directory is unavailable on this device."
            )

        output_dir = Path(downloads) / "Hyperkey"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def _ensure_form_default_output_directory(self) -> None:
        """
        Apply the Android default only when the user has not selected a custom
        output directory.

        Windows is intentionally left blank here. pipeline.py resolves its
        normal Windows default to the current user's Documents/Hyperkey folder.
        """
        if (self.output_directory_field.value or "").strip():
            return

        if not self._is_android():
            return

        output_dir = await self._get_android_default_output_directory()
        self.output_directory_field.value = str(output_dir)
        self._refresh_command_preview(None)

    @staticmethod
    def _arguments_have_output_directory(arguments: list[str]) -> bool:
        """Return True when CLI arguments already contain -o/--output."""
        for argument in arguments:
            value = str(argument).strip()
            if value in {"-o", "--output"} or value.startswith("--output="):
                return True
        return False

    # ------------------------------------------------------------------
    # Android storage permission
    # ------------------------------------------------------------------
    async def _android_all_files_access_granted(self) -> bool:
        """Return True when Android has granted Hyperkey All files access."""
        if not self._is_android():
            return True

        try:
            status = await self.permission_handler.get_status(
                fph.Permission.MANAGE_EXTERNAL_STORAGE
            )
            return status == fph.PermissionStatus.GRANTED
        except Exception:
            return False

    async def _request_android_all_files_access(self, _e=None) -> None:
        """
        Send the user to Android's special All files access permission screen.

        MANAGE_EXTERNAL_STORAGE is a special Android permission. The Flet
        permission handler opens the appropriate system settings screen rather
        than displaying a normal runtime-permission popup.
        """
        if not self._is_android():
            return

        try:
            self.page.pop_dialog()
        except Exception:
            pass

        try:
            status = await self.permission_handler.request(
                fph.Permission.MANAGE_EXTERNAL_STORAGE
            )

            # On Android this request can leave Hyperkey while the user toggles
            # "Allow access to manage all files" in system settings. Re-check
            # when control returns to the app instead of trusting the first
            # status value alone.
            granted = await self._android_all_files_access_granted()

            if granted:
                self.form_status.value = (
                    "File access granted. Hyperkey can now use direct custom "
                    "paths in shared storage."
                )
                self.form_status.color = ft.Colors.GREEN
            else:
                status_name = getattr(status, "name", "not granted")
                self.form_status.value = (
                    "All files access is not enabled. File/folder pickers will "
                    "still work, but manually entered Android paths may be "
                    f"inaccessible. Status: {status_name}."
                )
                self.form_status.color = ft.Colors.ORANGE

        except Exception as exc:
            self.form_status.value = f"Unable to request file access: {exc}"
            self.form_status.color = ft.Colors.RED

        self.page.update()

    async def _open_android_permission_settings(self, _e=None) -> None:
        """Open Hyperkey's Android app settings as a fallback."""
        if not self._is_android():
            return

        try:
            self.page.pop_dialog()
        except Exception:
            pass

        try:
            opened = await self.permission_handler.open_app_settings()
            if not opened:
                raise RuntimeError("Android app settings could not be opened.")
        except Exception as exc:
            self.form_status.value = f"Unable to open Android settings: {exc}"
            self.form_status.color = ft.Colors.RED
            self.page.update()

    def _show_android_storage_permission_dialog(self) -> None:
        """Explain All files access before sending the user to Android settings."""
        if not self._is_android():
            return

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Allow Hyperkey file access"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "Hyperkey can work with files selected through Android's "
                        "pickers without this permission."
                    ),
                    ft.Text(
                        "All files access is requested so Hyperkey can also read "
                        "and write direct custom paths that you enter manually, "
                        "including folders in shared internal storage."
                    ),
                    ft.Container(
                        padding=12,
                        border=ft.Border.all(1, ft.Colors.GREY_700),
                        border_radius=10,
                        content=ft.Column(
                            tight=True,
                            spacing=6,
                            controls=[
                                ft.Text(
                                    "Why Hyperkey needs it",
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text("• Read metadata CSV and spectral files from custom paths."),
                                ft.Text("• Read raw-data folders supplied as direct paths."),
                                ft.Text("• Save generated outputs to custom shared-storage folders."),
                                ft.Text("• Keep direct filesystem paths usable without copying files into app cache."),
                            ],
                        ),
                    ),
                    ft.Text(
                        "Android will open a system settings screen. Enable "
                        "“Allow access to manage all files” for Hyperkey, then "
                        "return to the app."
                    ),
                    ft.Text(
                        "This permission does not replace Hyperkey's secure "
                        "FileProvider-based Open action. Files handed to Excel, "
                        "PDF viewers, Gallery, and other apps still receive only "
                        "temporary access to the specific file being opened.",
                        theme_style=ft.TextThemeStyle.BODY_SMALL,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Not now", on_click=lambda _e: self.page.pop_dialog()),
                ft.Button(
                    content="Grant file access",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=self._request_android_all_files_access,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    async def ensure_android_storage_permission_on_startup(self) -> None:
        """
        On Android first launch (and later launches while permission is absent),
        explain why Hyperkey requests All files access before opening settings.
        """
        if not self._is_android():
            return

        if await self._android_all_files_access_granted():
            return

        self._show_android_storage_permission_dialog()

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
        input_card = self._section_panel(
            "Input data",
            subtitle="Choose the metadata and raw spectral-data sources.",
            icon=ft.Icons.DATA_OBJECT_OUTLINED,
            controls=[
                self._responsive_browse_field(
                    self.metadata_field,
                    self._pick_metadata,
                    button_text="Browse CSV",
                    button_icon=ft.Icons.UPLOAD_FILE,
                ),
                self._responsive_browse_field(
                    self.root_field,
                    self._pick_root_folder,
                    button_text="Browse folder",
                ),
                self._responsive_browse_field(
                    self.location_field,
                    self._pick_location,
                    button_text="Browse CSV",
                    button_icon=ft.Icons.UPLOAD_FILE,
                ),
            ],
        )

        output_card = self._section_panel(
            "Output",
            subtitle="Optional naming and destination settings.",
            icon=ft.Icons.FOLDER_COPY_OUTLINED,
            controls=[
                self.output_name_field,
                self._responsive_browse_field(
                    self.output_directory_field,
                    self._pick_output_folder,
                    button_text="Browse folder",
                ),
            ],
        )

        options_card = self._section_panel(
            "Analysis options",
            subtitle="Hyperkey's interface and generated visualisations share the same dark-mode setting.",
            icon=ft.Icons.TUNE,
            controls=[
                self._responsive_switches(),
                self._outlier_settings_panel(),
            ],
        )

        command_card = self._section_panel(
            "Equivalent CLI command",
            subtitle="Live preview of the command that will be executed.",
            icon=ft.Icons.TERMINAL,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        self.command_preview,
                        self.copy_command_button,
                    ],
                )
            ],
        )

        actions = ft.ResponsiveRow(
            spacing=10,
            run_spacing=8,
            controls=[
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                    content=self.run_button,
                ),
            ],
        )

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
                controls=[
                    self._screen_title(
                        "Run Hyperkey",
                        "Configure a processing job.",
                    ),
                    input_card,
                    output_card,
                    options_card,
                    command_card,
                    self.processing_bar,
                    self.form_status,
                    actions,
                    ft.Container(height=18),
                ],
            ),
        )

    def _cli_screen(self) -> ft.Control:
        cli_card = self._section_panel(
            "CLI input",
            subtitle="Paste Hyperkey arguments or a complete python hyperkey.py command.",
            icon=ft.Icons.TERMINAL,
            controls=[
                self.cli_field,
                ft.Text(
                    "Example: metadata.csv -r raw_data "
                    "-o output_folder -n sydneyAPPN "
                    "-l species_locations.csv --outlier-analysis",
                    theme_style=ft.TextThemeStyle.BODY_SMALL,
                    selectable=True,
                ),
            ],
        )

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
                controls=[
                    self._screen_title(
                        "Advanced argument mode",
                        "Failsafe mode for technical users who prefer direct CLI control.",
                    ),
                    cli_card,
                    self.cli_status,
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                col={"xs": 12, "sm": 6, "md": 4},
                                content=self.cli_run_button,
                            )
                        ]
                    ),
                    ft.Container(height=18),
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
                spacing=14,
                controls=[
                    self._screen_title("Results", "Run statistics and backend execution details."),
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
            ("Markdown report", summary.get("report_markdown_output")),
            ("HTML report", summary.get("report_html_output")),
            ("PDF report", summary.get("report_pdf_output")),
            ("Heatmap", summary.get("heatmap_output")),
            ("Spectral graph", summary.get("spectral_graph_output")),
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
        """Open a generated file with a compatible external application.

        Android must not expose a raw file:// URI to another application.
        Hyperkey therefore delegates Android opening to the bundled
        HyperkeyFileOpener extension, which uses an Android FileProvider-backed
        ACTION_VIEW intent and grants the chosen viewer temporary read access.
        Desktop platforms continue using Flet's UrlLauncher.
        """
        try:
            resolved = path.resolve()

            if not resolved.exists() or not resolved.is_file():
                raise FileNotFoundError(f"Generated file not found: {resolved}")

            if self._is_android():
                if self.android_file_opener is None:
                    raise RuntimeError(
                        "Android file opener extension is not installed. "
                        "Add hyperkey-file-opener to the app dependencies and rebuild the APK."
                    )

                mime_type, _encoding = mimetypes.guess_type(str(resolved))
                await self.android_file_opener.open_file(
                    str(resolved),
                    mime_type=mime_type,
                )
            else:
                await self.url_launcher.launch_url(
                    resolved.as_uri(),
                    mode=ft.LaunchMode.EXTERNAL_APPLICATION,
                )

            self.output_status.value = f"Opening: {resolved.name}"

        except Exception as exc:
            self.output_status.value = (
                f"Unable to open '{path.name}': {exc}"
            )

        self.page.update()

    async def _share_output_path(self, path: Path) -> None:
        """Share a generated file using the platform share sheet."""
        try:
            resolved = path.resolve()

            if not resolved.exists() or not resolved.is_file():
                raise FileNotFoundError(f"Generated file not found: {resolved}")

            await self.share_service.share_files(
                [ft.ShareFile.from_path(str(resolved))],
                title=f"Share {resolved.name}",
            )
            self.output_status.value = f"Sharing: {resolved.name}"

        except Exception as exc:
            self.output_status.value = (
                f"Unable to share '{path.name}': {exc}"
            )

        self.page.update()

    def _output_file_card(self, label: str, path: Path) -> ft.Card:
        async def open_file(_e) -> None:
            await self._open_output_path(path)

        async def share_file(_e) -> None:
            await self._share_output_path(path)

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
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED),
                                ft.Column(
                                    expand=True,
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            label,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                        ft.Text(
                                            subtitle,
                                            max_lines=3,
                                            size=12,
                                            selectable=True,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            spacing=8,
                            wrap=True,
                            controls=[
                                ft.Button(
                                    content="Open",
                                    icon=ft.Icons.OPEN_IN_NEW,
                                    on_click=open_file,
                                ),
                                ft.OutlinedButton(
                                    content="Share",
                                    icon=ft.Icons.SHARE_OUTLINED,
                                    on_click=share_file,
                                ),
                            ],
                        ),
                    ],
                ),
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
                spacing=14,
                controls=[
                    self._screen_title(
                        "Outputs",
                        "Generated files from the latest run. Open them with a compatible app or share them without closing Hyperkey.",
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

        # --------------------------------------------------------------
        # Report preview - output tab below
        # --------------------------------------------------------------
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
        else:
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
            else:
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
                                    # A long unwanted space issue, need fix later.
                                    # Feature not requested by user, so commented out for now.
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

        # --------------------------------------------------------------
        # Generated files 
        # --------------------------------------------------------------
        generated_files = self._generated_output_files()

        if generated_files:
            self.outputs_content.controls.append(
                section_card(
                    "Generated files",
                    subtitle="Open a file with a compatible application or share it.",
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

    def _logs_screen(self) -> ft.Control:
        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=14,
                controls=[
                    self._screen_title("Logs", "Execution messages from the latest Hyperkey run."),
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
                        self._style_input_field(ft.TextField(
                            label="Executed / prepared command",
                            read_only=True,
                            multiline=True,
                            min_lines=4,
                            max_lines=8,
                            value=self.service.format_command(result.arguments),
                        )),
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

    async def _copy_command(self, _e) -> None:
        """Copy the generated CLI command to the system clipboard."""
        command = (self.command_preview.value or "").strip()

        if not command:
            self.form_status.value = "No command available to copy."
            self.page.update()
            return

        try:
            await ft.Clipboard().set(command)
            self.form_status.value = "CLI command copied to clipboard."
            self.form_status.color = ft.Colors.GREEN
        except Exception as exc:
            self.form_status.value = f"Unable to copy command: {exc}"
            self.form_status.color = ft.Colors.RED

        self.page.update()

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
            # Default output policy:
            #   Windows -> Documents/Hyperkey (resolved by pipeline.py)
            #   Android -> Downloads/Hyperkey (resolved here through Flet)
            # A user-selected output directory still overrides either default.
            await self._ensure_form_default_output_directory()

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

            # Keep Advanced CLI mode consistent with the normal form:
            # Android defaults to Downloads/Hyperkey only when the command
            # does not already contain -o/--output.
            if (
                self._is_android()
                and not self._arguments_have_output_directory(arguments)
            ):
                android_output = (
                    await self._get_android_default_output_directory()
                )
                arguments.extend(["-o", str(android_output)])

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

        # Move to Outputs after a valid run. Invalid input stays on the current screen.
        if result.success:
            self.current_screen = 3
            self.navigation.selected_index = 3
            self._render_screen()
        else:
            self.page.update()

    def _system_is_dark(self) -> bool:
        """Return True when the host operating system is currently using dark mode."""
        return self.page.platform_brightness == ft.Brightness.DARK

    def _apply_dark_mode(self, enabled: bool, *, refresh_preview: bool = True) -> None:
        """
        Apply one dark-mode state to both the Flet interface and generated
        visualisations.
        """
        self.page.theme_mode = ft.ThemeMode.DARK if enabled else ft.ThemeMode.LIGHT
        self.dark_mode_switch.value = enabled
        self.theme_button.icon = (
            ft.Icons.LIGHT_MODE_OUTLINED
            if enabled
            else ft.Icons.DARK_MODE_OUTLINED
        )

        if refresh_preview:
            self._refresh_command_preview(None)
        elif self._mounted:
            self.page.update()

    def _on_dark_mode_switch_change(self, e) -> None:
        """Keep the app theme and visualisation dark-mode option synchronized."""
        self._apply_dark_mode(bool(e.control.value))

    def _on_platform_brightness_change(self, _e) -> None:
        """Follow changes to the operating system's current appearance."""
        self._apply_dark_mode(self._system_is_dark())

    def _toggle_app_theme(self, _e) -> None:
        """Toggle both the application theme and generated visualisations."""
        self._apply_dark_mode(not bool(self.dark_mode_switch.value))

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
                        "Optional output-name prefix. It is passed separately as -n/--name. Existing Hyperkey dated naming is preserved by the backend.",
                    ),
                    help_item(
                        "Output directory",
                        "Optional destination directory for generated outputs. If empty, Windows uses Documents/Hyperkey and Android uses Downloads/Hyperkey. A selected folder is passed separately as -o/--output and overrides the default.",
                    ),
                    help_item(
                        "Dark mode",
                        "Hyperkey follows the operating system light/dark preference by default. The top-right theme button and this switch are synchronized, and the same setting is used for generated visualisations.",
                    ),
                    help_item(
                        "Outlier analysis",
                        "Runs the outlier-analysis stage when enabled. Expand Outlier settings to optionally override SD threshold, maximum outliers, ID column, grouping, minimum valid values, or DDOF. Empty fields keep the stored backend defaults.",
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
                        "Shows the files generated by the latest successful run. Use Open to launch a compatible application or Share to send the file through Android/Windows sharing. The Markdown report is also previewed directly inside the app.",
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


async def main(page: ft.Page) -> None:
    ui = HyperkeyUI(page)
    await ui.ensure_android_storage_permission_on_startup()


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir="assets",
    )   