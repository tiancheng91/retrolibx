"""Pegasus frontend adapter."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from retrolibx.core.models import (
    Capabilities,
    Diagnostic,
    Game,
    LaunchConfig,
    Library,
    Media,
    Rom,
    System,
)
from retrolibx.core.normalize import parse_bool, parse_date, parse_players
from retrolibx.core.operations import ExportIntent, FileRequest, TextRequest
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.errors import ParseError
from retrolibx.utils import FileIndex, find_metadata

from ..base import DetectionResult, ImportResult, LibraryAdapter
from .metadata import field, parse_metadata, render_records


class PegasusAdapter(LibraryAdapter):
    name = "pegasus"
    aliases = ()
    capabilities = Capabilities(
        artwork=True, video=True, collections=True, favorites=True, launch_config=True
    )

    @staticmethod
    def _metadata_files(path: Path) -> list[Path]:
        return find_metadata(path, ("metadata.pegasus.txt",))

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        files = cls._metadata_files(path)
        return DetectionResult(
            format=cls.name,
            confidence=0.96 if files else 0.0,
            evidence=[f"{len(files)} Pegasus metadata file(s)"] if files else [],
        )

    def import_library(self, path: Path, options: ImportOptions) -> ImportResult:
        del options
        root = path if path.is_dir() else path.parent
        metadata_files = self._metadata_files(path)
        resolver = FileIndex(root, exclude=metadata_files)
        systems: list[System] = []
        diagnostics: list[Diagnostic] = []
        for metadata_path in metadata_files:
            try:
                text = metadata_path.read_text(encoding="utf-8-sig")
            except OSError as exc:
                raise ParseError(f"Could not read {metadata_path}: {exc}") from exc
            records = parse_metadata(text)
            collection: dict[str, list[str]] = {}
            game_records: list[dict[str, list[str]]] = []
            for record in records:
                if "collection" in record and "game" not in record:
                    collection.update(record)
                elif "game" in record:
                    game_records.append(record)
            collection_name = field(collection, "collection") or metadata_path.parent.name
            shortname = field(collection, "shortname") or collection_name
            system_record = self.systems.resolve(shortname) or self.systems.resolve(collection_name)
            system = System(
                id=system_record.id if system_record else shortname.casefold().replace(" ", "-"),
                name=system_record.name if system_record else collection_name,
                metadata={"pegasus": collection},
            )
            for record in game_records:
                filenames = record.get("file", [])
                if not filenames:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="missing-rom-reference",
                            message="Pegasus game has no file",
                            path=metadata_path,
                            game_name=field(record, "game"),
                        )
                    )
                    continue
                roms = []
                for filename in filenames:
                    resolved = resolver.resolve(
                        filename,
                        bases=(metadata_path.parent,),
                        preferred_parts=("rom", "roms", system.id),
                    )
                    roms.append(
                        Rom(
                            path=resolved
                            or (metadata_path.parent / filename).resolve(strict=False),
                            metadata={"source_path": filename},
                        )
                    )
                players_min, players_max = parse_players(field(record, "players"))
                raw_rating = field(record, "rating")
                try:
                    rating = float(raw_rating) if raw_rating else None
                    if rating is not None and rating > 1:
                        rating /= 100.0
                    if rating is not None:
                        rating = max(0.0, min(1.0, rating))
                except ValueError:
                    rating = None
                assets: dict[str, Path] = {}
                for key, values in record.items():
                    if not key.startswith("assets.") or not values:
                        continue
                    kind = key.removeprefix("assets.")
                    value = values[-1]
                    assets[kind] = resolver.resolve(
                        value,
                        bases=(metadata_path.parent,),
                        preferred_parts=("media", "images", kind),
                    ) or (metadata_path.parent / value).resolve(strict=False)
                media = Media(
                    box_front=assets.pop("boxFront", assets.pop("box_front", None)),
                    screenshot=assets.pop("screenshot", None),
                    logo=assets.pop("logo", None),
                    video=assets.pop("video", None),
                    extra=assets,
                )
                known = {
                    "game",
                    "file",
                    "sort",
                    "description",
                    "developer",
                    "publisher",
                    "genre",
                    "release",
                    "players",
                    "rating",
                    "favorite",
                    "launch",
                }
                unknown = {
                    key: value
                    for key, value in record.items()
                    if key not in known and not key.startswith("assets.")
                }
                game_name = field(record, "game") or Path(filenames[0]).stem
                system.games.append(
                    Game(
                        name=game_name,
                        sort_name=field(record, "sort"),
                        roms=roms,
                        media=media,
                        description=field(record, "description"),
                        developer=field(record, "developer"),
                        publisher=field(record, "publisher"),
                        genre=[
                            part.strip()
                            for part in re.split(r"[,;]", field(record, "genre") or "")
                            if part.strip()
                        ],
                        release_date=parse_date(field(record, "release")),
                        players_min=players_min,
                        players_max=players_max,
                        rating=rating,
                        favorite=parse_bool(field(record, "favorite")),
                        launch=LaunchConfig(command=field(record, "launch"))
                        if field(record, "launch")
                        else None,
                        source_metadata={"pegasus": unknown},
                    )
                )
            systems.append(system)
        library = Library(
            format=self.name, source_path=root, systems=systems, diagnostics=diagnostics
        )
        return ImportResult(library=library, diagnostics=diagnostics)

    def render_library(
        self, library: Library, target: Path, options: ExportOptions
    ) -> ExportIntent:
        del target, options
        intent = ExportIntent()
        for system in sorted(library.systems, key=lambda item: item.id):
            record = self.systems.records.get(system.id)
            mapping = record.platforms.get("pegasus") if record else None
            directory = mapping.shortname[0] if mapping and mapping.shortname else system.id
            collection_fields: list[tuple[str, str | None]] = [
                ("collection", system.name),
                ("shortname", directory),
            ]
            extensions = sorted(
                {
                    rom.path.suffix.lstrip(".")
                    for game in system.games
                    for rom in game.roms
                    if rom.path.suffix
                }
            )
            collection_fields.append(("extension", " ".join(extensions)))
            records: list[list[tuple[str, str | None]]] = [collection_fields]
            for game in sorted(system.games, key=lambda item: item.sort_name or item.name):
                game_fields: list[tuple[str, str | None]] = [("game", game.name)]
                for rom in game.roms:
                    destination = PurePosixPath(directory) / rom.path.name
                    intent.files.append(
                        FileRequest(source=rom.path, destination=destination, category="rom")
                    )
                    game_fields.append(("file", rom.path.name))
                game_fields.extend(
                    [
                        ("sort", game.sort_name),
                        ("description", game.description),
                        ("developer", game.developer),
                        ("publisher", game.publisher),
                        ("genre", ", ".join(game.genre) or None),
                        ("release", game.release_date.isoformat() if game.release_date else None),
                        ("players", self._players(game)),
                        (
                            "rating",
                            str(round(game.rating * 100)) if game.rating is not None else None,
                        ),
                        (
                            "favorite",
                            "true"
                            if game.favorite
                            else "false"
                            if game.favorite is not None
                            else None,
                        ),
                        ("launch", game.launch.command if game.launch else None),
                    ]
                )
                for kind, media in game.media.items():
                    destination = (
                        PurePosixPath(directory)
                        / "media"
                        / f"{Path(game.roms[0].path).stem}-{kind}{media.suffix or '.png'}"
                    )
                    intent.files.append(
                        FileRequest(source=media, destination=destination, category="media")
                    )
                    game_fields.append((f"assets.{kind}", f"media/{destination.name}"))
                records.append(game_fields)
            intent.texts.append(
                TextRequest(
                    destination=PurePosixPath(directory) / "metadata.pegasus.txt",
                    content=render_records(records),
                )
            )
        return intent

    @staticmethod
    def _players(game: Game) -> str | None:
        if game.players_min is None:
            return None
        if game.players_max is None or game.players_max == game.players_min:
            return str(game.players_min)
        return f"{game.players_min}-{game.players_max}"
