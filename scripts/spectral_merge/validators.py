from __future__ import annotations


def is_valid_filenum(value: object) -> bool:
    """Return True when FileNum is an integer in the valid 0000-9999 range."""
    if value is None:
        return False
    text = str(value).strip()
    return text.isdigit() and 0 <= int(text) <= 9999


def format_filenum(value: object) -> str:
    """Return a zero-padded 4 digit FileNum when possible."""
    try:
        return str(int(str(value).strip())).zfill(4)
    except Exception:
        return str(value)
