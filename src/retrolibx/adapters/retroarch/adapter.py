"""RetroArch adapter."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from retrolibx.core.models import Capabilities, Diagnostic, Game, LaunchConfig, Library, Rom, System
from retrolibx.core.operations import ExportIntent, FileRequest, TextRequest
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.errors import ParseError

from ..base import DetectionResult, ImportResult, LibraryAdapter
from .media import media_destination, resolve_media
from .playlist import read_playlist, write_playlist


class RetroArchAdapter(LibraryAdapter):
    name = "retroarch"
    aliases = ("ra",)
    capabilities = Capabilities(artwork=True, launch_config=True)

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        playlist_dir = path / "playlists" if path.is_dir() else path.parent
        files = list(playlist_dir.glob("*.lpl")) if playlist_dir.is_dir() else []
        confidence = 0.95 if files and playlist_dir.name == "playlists" else 0.75 if files else 0.0
        return DetectionResult(
            format=cls.name,
            confidence=confidence,
            evidence=[f"{len(files)} RetroArch playlist(s)"] if files else [],
        )

    def import_library(self, path: Path, options: ImportOptions) -> ImportResult:
        del options
        root = path if path.is_dir() else path.parent
        playlist_dir = root / "playlists" if (root / "playlists").is_dir() else root
        diagnostics: list[Diagnostic] = []
        systems: list[System] = []
        for playlist in sorted(playlist_dir.glob("*.lpl")):
            record = self.systems.resolve(playlist.stem)
            system_id = record.id if record else playlist.stem.casefold().replace(" ", "-")
            system = System(
                id=system_id,
                name=record.name if record else playlist.stem,
                metadata={"retroarch": {"playlist": playlist.name}},
            )
            try:
                items = read_playlist(playlist)
            except ParseError as exc:
                diagnostics.append(
                    Diagnostic(
                        severity="error", code="invalid-playlist", message=str(exc), path=playlist
                    )
                )
                continue
            for item in items:
                raw_path = str(item.get("path", "")).strip()
                label = str(item.get("label") or Path(raw_path).stem or "Unknown")
                if not raw_path:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="missing-rom-reference",
                            message="Playlist item has no path",
                            path=playlist,
                            game_name=label,
                        )
                    )
                    continue
                rom_path = Path(raw_path).expanduser()
                if not rom_path.is_absolute():
                    rom_path = (root / rom_path).resolve(strict=False)
                launch = LaunchConfig(
                    core=str(item.get("core_name"))
                    if item.get("core_name") not in (None, "DETECT")
                    else None,
                    metadata={"core_path": item.get("core_path")},
                )
                known = {"path", "label", "core_path", "core_name", "crc32", "db_name"}
                unknown: dict[str, Any] = {
                    key: value for key, value in item.items() if key not in known
                }
                game = Game(
                    name=label,
                    roms=[
                        Rom(path=rom_path, crc32=str(item["crc32"]) if item.get("crc32") else None)
                    ],
                    media=resolve_media(root, playlist.stem, label),
                    launch=launch,
                    source_metadata={"retroarch": {"db_name": item.get("db_name"), **unknown}},
                )
                system.games.append(game)
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
            mapping = record.platforms.get("retroarch") if record else None
            playlist_name = mapping.playlist[0] if mapping and mapping.playlist else system.name
            items: list[dict[str, Any]] = []
            for game in sorted(system.games, key=lambda item: item.sort_name or item.name):
                for rom in game.roms:
                    destination = PurePosixPath("roms") / system.id / rom.path.name
                    intent.files.append(
                        FileRequest(source=rom.path, destination=destination, category="rom")
                    )
                    source = game.source_metadata.get("retroarch", {})
                    launch = game.launch
                    items.append(
                        {
                            "path": str(destination),
                            "label": game.name,
                            "core_path": launch.metadata.get("core_path", "DETECT")
                            if launch
                            else "DETECT",
                            "core_name": launch.core or "DETECT" if launch else "DETECT",
                            "crc32": rom.crc32 or "DETECT",
                            "db_name": source.get("db_name") or f"{playlist_name}.lpl",
                        }
                    )
                for kind, media in game.media.items():
                    if kind not in {"box_front", "screenshot", "title_screen"}:
                        continue
                    relative = media_destination(
                        playlist_name, game.name, kind, media.suffix or ".png"
                    )
                    intent.files.append(
                        FileRequest(
                            source=media,
                            destination=PurePosixPath(relative.as_posix()),
                            category="media",
                        )
                    )
            intent.texts.append(
                TextRequest(
                    destination=PurePosixPath("playlists") / f"{playlist_name}.lpl",
                    content=write_playlist(items),
                )
            )
        return intent
