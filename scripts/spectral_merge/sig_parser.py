from __future__ import annotations

import os


def parse_sig_file(filepath: str) -> tuple[list[str] | None, list[str] | None]:
    """
    Parse a .sig file and return wavelengths plus reflectance values.

    The parser keeps the original logic: after the line 'data=', it reads rows with
    at least four whitespace-separated columns and uses column 1 as wavelength and
    column 4 as reflectance.
    """
    wavelengths: list[str] = []
    reflectance: list[str] = []
    data_section = False

    try:
        if not os.path.exists(filepath):
            return None, None

        with open(filepath, "r", encoding="utf-8", errors="ignore") as sig_file:
            for raw_line in sig_file:
                line = raw_line.strip()

                if line == "data=":
                    data_section = True
                    continue

                if data_section and line:
                    parts = line.split()
                    if len(parts) >= 4:
                        wavelengths.append(parts[0])
                        reflectance.append(parts[3])

        return wavelengths, reflectance
    except Exception:
        return None, None
