"""RetroLibX intermediate representation (RLX IR)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RLXModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Diagnostic(RLXModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    path: Path | None = None
    system_id: str | None = None
    game_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class Capabilities(RLXModel):
    metadata: bool = True
    artwork: bool = True
    video: bool = False
    collections: bool = False
    favorites: bool = False
    play_stats: bool = False
    launch_config: bool = False


class LaunchConfig(RLXModel):
    emulator: str | None = None
    core: str | None = None
    command: str | None = None
    working_directory: Path | None = None
    args: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Rom(RLXModel):
    path: Path
    name: str | None = None
    size: int | None = None
    crc32: str | None = None
    md5: str | None = None
    sha1: str | None = None
    disc: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Media(RLXModel):
    box_front: Path | None = None
    box_back: Path | None = None
    screenshot: Path | None = None
    title_screen: Path | None = None
    logo: Path | None = None
    marquee: Path | None = None
    fanart: Path | None = None
    video: Path | None = None
    manual: Path | None = None
    music: Path | None = None
    extra: dict[str, Path] = Field(default_factory=dict)

    def items(self) -> list[tuple[str, Path]]:
        result: list[tuple[str, Path]] = []
        for name in self.__class__.model_fields:
            if name == "extra":
                continue
            value = getattr(self, name)
            if isinstance(value, Path):
                result.append((name, value))
        result.extend(sorted(self.extra.items()))
        return result


class Game(RLXModel):
    id: str | None = None
    name: str
    sort_name: str | None = None
    roms: list[Rom] = Field(default_factory=list)
    media: Media = Field(default_factory=Media)
    description: str | None = None
    developer: str | None = None
    publisher: str | None = None
    genre: list[str] = Field(default_factory=list)
    release_date: date | None = None
    players_min: int | None = None
    players_max: int | None = None
    rating: float | None = None
    favorite: bool | None = None
    hidden: bool | None = None
    play_count: int | None = None
    last_played: datetime | None = None
    launch: LaunchConfig | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("rating must be between 0 and 1")
        return value


class System(RLXModel):
    id: str
    name: str
    short_name: str | None = None
    platform_ids: list[str] = Field(default_factory=list)
    games: list[Game] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Collection(RLXModel):
    id: str
    name: str
    game_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Library(RLXModel):
    format: str
    source_path: Path | None = None
    systems: list[System] = Field(default_factory=list)
    collections: list[Collection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)

    @property
    def game_count(self) -> int:
        return sum(len(system.games) for system in self.systems)

    @property
    def media_count(self) -> int:
        return sum(len(game.media.items()) for system in self.systems for game in system.games)
