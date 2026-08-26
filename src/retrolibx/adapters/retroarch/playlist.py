"""RetroArch playlist codec."""

import json
from pathlib import Path
from typing import Any

from retrolibx.errors import ParseError


def read_playlist(path: Path) -> list[dict[str, Any]]:
    try:
        data: object = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParseError(f"Invalid RetroArch playlist {path}: {exc}") from exc
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ParseError(f"Playlist root must be an object or array: {path}")
    if not isinstance(items, list):
        raise ParseError(f"Playlist items must be an array: {path}")
    return [item for item in items if isinstance(item, dict)]


def write_playlist(items: list[dict[str, Any]]) -> str:
    payload = {"version": "1.5", "default_core_path": "", "default_core_name": "", "items": items}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
