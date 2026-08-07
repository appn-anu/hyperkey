from __future__ import annotations

import os
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

        # Results/log controls
        self.results_content = ft.Column(spacing=12)
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
        screens = [self._run_screen, self._cli_screen, self._results_screen, self._logs_screen]
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

    def _run_form(self, _e) -> None:
        self.processing_bar.visible = True
        self.run_button.disabled = True
        self.form_status.value = "Running Hyperkey..."
        self.page.update()

        try:
            config = self._config_from_form()
            result = self.service.run_config(config)
        except Exception as exc:
            result = RunResult(False, f"Unable to start Hyperkey: {exc}", logs=[f"ERROR: {exc}"])
        finally:
            self.processing_bar.visible = False
            self.run_button.disabled = False

        self._handle_result(result, self.form_status)

    def _run_cli(self, _e) -> None:
        self.cli_run_button.disabled = True
        self.cli_status.value = "Running Hyperkey arguments..."
        self.page.update()

        try:
            arguments = self.service.parse_cli_text(self.cli_field.value or "")
            result = self.service.run_arguments(arguments)
        except Exception as exc:
            result = RunResult(False, f"Invalid command/arguments: {exc}", logs=[f"ERROR: {exc}"])
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
