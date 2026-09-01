from __future__ import annotations

import flet as ft


@ft.control("HyperkeyFileOpener")
class HyperkeyFileOpener(ft.Service):
    """Open local files using the host platform's native file-opening mechanism."""

    async def open_file(self, path: str, mime_type: str | None = None):
        return await self._invoke_method(
            "open_file",
            {
                "path": path,
                "mime_type": mime_type,
            },
        )
