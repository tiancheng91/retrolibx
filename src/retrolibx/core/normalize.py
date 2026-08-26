"""Stable normalization helpers."""

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

_TAGS = re.compile(r"\s*[\[(][^\])]*[\])]\s*")
_SPACE = re.compile(r"\s+")


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = _TAGS.sub(" ", value)
    return _SPACE.sub(" ", value).strip().casefold()


def normalized_filename(path: str | Path) -> str:
    return normalized_name(Path(path).stem)


def parse_bool(value: str | None) -> bool | None:
    if value is None or not value.strip():
        return None
    return value.strip().casefold() in {"1", "true", "yes"}


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    compact = value.strip().replace("-", "")
    try:
        return datetime.strptime(compact[:8], "%Y%m%d").date()
    except ValueError:
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    compact = value.strip().replace("-", "").replace(":", "").replace("T", "")
    for fmt, length in (("%Y%m%d%H%M%S", 14), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(compact[:length], fmt)
        except ValueError:
            pass
    return None


def parse_players(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    numbers = [int(item) for item in re.findall(r"\d+", value)]
    if not numbers:
        return None, None
    return (numbers[0], numbers[-1]) if len(numbers) > 1 else (numbers[0], numbers[0])
