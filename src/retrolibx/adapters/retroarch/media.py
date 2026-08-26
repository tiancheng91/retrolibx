"""RetroArch thumbnail resolution."""

from pathlib import Path

from retrolibx.core.models import Media

_INVALID = str.maketrans(
    {
        "&": "_",
        "*": "_",
        "/": "_",
        ":": "_",
        "`": "_",
        "<": "_",
        ">": "_",
        "?": "_",
        "\\": "_",
        "|": "_",
        '"': "_",
    }
)
_KINDS = {"Named_Boxarts": "box_front", "Named_Snaps": "screenshot", "Named_Titles": "title_screen"}


def thumbnail_name(label: str) -> str:
    return label.translate(_INVALID)


def resolve_media(root: Path, playlist_name: str, label: str) -> Media:
    media = Media()
    stem = thumbnail_name(label)
    for directory, field in _KINDS.items():
        for extension in (".png", ".jpg", ".jpeg"):
            candidate = root / "thumbnails" / playlist_name / directory / f"{stem}{extension}"
            if candidate.is_file():
                setattr(media, field, candidate)
                break
    return media


def media_destination(playlist_name: str, label: str, kind: str, suffix: str) -> Path:
    directories = {
        "box_front": "Named_Boxarts",
        "screenshot": "Named_Snaps",
        "title_screen": "Named_Titles",
    }
    return (
        Path("thumbnails") / playlist_name / directories[kind] / f"{thumbnail_name(label)}{suffix}"
    )
