"""User-selectable import and export policies."""

from enum import StrEnum

from pydantic import BaseModel


class RomMode(StrEnum):
    COPY = "copy"
    MOVE = "move"
    SYMLINK = "symlink"
    LINK = "link"
    HARDLINK = "hardlink"
    NONE = "none"


class MediaMode(StrEnum):
    COPY = "copy"
    SYMLINK = "symlink"
    HARDLINK = "hardlink"


class ConflictPolicy(StrEnum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    ERROR = "error"
    NEWER = "newer"


class ImportOptions(BaseModel):
    calculate_hashes: bool = False
    game_name_field: str = "label"


class ExportOptions(BaseModel):
    rom_mode: RomMode = RomMode.COPY
    media_mode: MediaMode = MediaMode.COPY
    conflict: ConflictPolicy = ConflictPolicy.SKIP
    in_place: bool = False
