"""Pegasus metadata stanza parser and writer."""

from __future__ import annotations

from collections.abc import Iterable


def parse_metadata(text: str) -> list[dict[str, list[str]]]:
    records: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] = {}
    last_key: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            if current:
                records.append(current)
                current = {}
            last_key = None
            continue
        if raw_line[:1].isspace() and last_key:
            current[last_key][-1] += "\n" + raw_line.strip()
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        last_key = key.strip().casefold()
        current.setdefault(last_key, []).append(value.strip())
    if current:
        records.append(current)
    return records


def field(record: dict[str, list[str]], key: str) -> str | None:
    values = record.get(key)
    return values[-1] if values else None


def render_records(records: Iterable[list[tuple[str, str | None]]]) -> str:
    blocks: list[str] = []
    for record in records:
        lines: list[str] = []
        for key, value in record:
            if value is None or value == "":
                continue
            parts = str(value).splitlines() or [""]
            lines.append(f"{key}: {parts[0]}")
            lines.extend(f"  {part}" for part in parts[1:])
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"
