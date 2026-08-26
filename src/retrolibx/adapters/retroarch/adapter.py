"""RetroArch adapter."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from retrolibx.core.models import Capabilities, Diagnostic, Game, LaunchConfig, Library, Rom, System
from retrolibx.core.operations import ExportIntent, FileRequest, TextRequest
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.errors import ParseError
from retrolibx.utils import FileIndex, find_metadata

from ..base import DetectionResult, ImportResult, LibraryAdapter
from .media import media_destination, resolve_media
from .playlist import read_playlist, write_playlist


class RetroArchAdapter(LibraryAdapter):
    name = "retroarch"
    aliases = ("ra",)
    capabilities = Capabilities(artwork=True, launch_config=True)

    @staticmethod
    def _layout(path: Path) -> tuple[Path, Path, Path]:
        """Return RetroArch root, playlist directory, and enclosing package root."""
        if path.is_file():
            playlist_dir = path.parent
            root = (
                playlist_dir.parent if playlist_dir.name.casefold() == "playlists" else playlist_dir
            )
            return root, playlist_dir, root.parent

        direct = path / "playlists"
        if direct.is_dir():
            return path, direct, path.parent

        if path.is_dir():
            nested_roots = sorted(
                child
                for child in path.iterdir()
                if child.is_dir()
                and child.name.casefold() == "retroarch"
                and (child / "playlists").is_dir()
            )
            if nested_roots:
                root = nested_roots[0]
                return root, root / "playlists", path

        return path, path, path.parent

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        root, _, package_root = cls._layout(path)
        files = find_metadata(path, ("*.lpl",))
        nested = root != path and package_root == path
        conventional = any(item.parent.name.casefold() == "playlists" for item in files)
        confidence = 0.95 if files and conventional else 0.75 if files else 0.0
        evidence = [f"{len(files)} RetroArch playlist(s)"] if files else []
        if nested:
            evidence.append(f"nested RetroArch directory: {root.name}")
        return DetectionResult(
            format=cls.name,
            confidence=confidence,
            evidence=evidence,
        )

    def import_library(self, path: Path, options: ImportOptions) -> ImportResult:
        root = path if path.is_dir() else path.parent
        playlists = find_metadata(path, ("*.lpl",))
        resolver = FileIndex(root, exclude=playlists)
        diagnostics: list[Diagnostic] = []
        systems: list[System] = []
        for playlist in playlists:
            playlist_root = (
                playlist.parent.parent
                if playlist.parent.name.casefold() == "playlists"
                else playlist.parent
            )
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
                resource_label = str(item.get("label") or Path(raw_path).stem or "Unknown")
                configured_name = item.get(options.game_name_field)
                game_name = str(configured_name).strip() if configured_name is not None else ""
                if not game_name:
                    game_name = resource_label
                if not raw_path:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="missing-rom-reference",
                            message="Playlist item has no path",
                            path=playlist,
                            game_name=game_name,
                        )
                    )
                    continue
                rom_path = resolver.resolve(
                    raw_path,
                    bases=(playlist.parent, playlist_root),
                    preferred_parts=("rom", "roms", system.id),
                )
                if rom_path is None:
                    source_path = Path(raw_path).expanduser()
                    rom_path = (
                        source_path
                        if source_path.is_absolute()
                        else (playlist_root / source_path).resolve(strict=False)
                    )
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
                    name=game_name,
                    roms=[
                        Rom(path=rom_path, crc32=str(item["crc32"]) if item.get("crc32") else None)
                    ],
                    media=resolve_media(playlist_root, playlist.stem, resource_label, resolver),
                    launch=launch,
                    source_metadata={
                        "retroarch": {
                            "db_name": item.get("db_name"),
                            "resource_label": resource_label,
                            "game_name_field": options.game_name_field,
                            **unknown,
                        }
                    },
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
