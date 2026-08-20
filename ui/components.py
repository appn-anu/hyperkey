from __future__ import annotations

import flet as ft


BREAKPOINT_COL = {
    ft.ResponsiveRowBreakpoint.XS: 12,
    ft.ResponsiveRowBreakpoint.MD: 6,
}


def section_header(title: str, subtitle: str | None = None) -> ft.Column:
    controls: list[ft.Control] = [
        ft.Text(title, theme_style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600)
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, theme_style=ft.TextThemeStyle.BODY_SMALL))
    return ft.Column(controls=controls, spacing=2)


def section_card(title: str, controls: list[ft.Control], subtitle: str | None = None) -> ft.Card:
    return ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                controls=[section_header(title, subtitle), ft.Divider(), *controls],
                spacing=12,
            ),
        )
    )


def browse_field(
    text_field: ft.TextField,
    on_browse,
    button_text: str = "Browse",
    button_icon=ft.Icons.FOLDER_OPEN,
) -> ft.ResponsiveRow:
    text_field.col = {
        ft.ResponsiveRowBreakpoint.XS: 12,
        ft.ResponsiveRowBreakpoint.SM: 9,
    }
    button = ft.Button(
        content=button_text,
        icon=button_icon,
        on_click=on_browse,
        col={
            ft.ResponsiveRowBreakpoint.XS: 12,
            ft.ResponsiveRowBreakpoint.SM: 3,
        },
    )
    return ft.ResponsiveRow(controls=[text_field, button], spacing=8, run_spacing=8)


def stat_card(label: str, value: str, icon) -> ft.Card:
    return ft.Card(
        col=BREAKPOINT_COL,
        content=ft.Container(
            padding=16,
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=28),
                    ft.Column(
                        controls=[
                            ft.Text(value, theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                            ft.Text(label, theme_style=ft.TextThemeStyle.BODY_SMALL),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=12,
            ),
        ),
    )


def help_item(title: str, body: str) -> ft.Column:
    return ft.Column(
        controls=[
            ft.Text(title, weight=ft.FontWeight.W_600),
            ft.Text(body, theme_style=ft.TextThemeStyle.BODY_SMALL),
        ],
        spacing=2,
    )
