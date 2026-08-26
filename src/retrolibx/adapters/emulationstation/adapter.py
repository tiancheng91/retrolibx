"""Generic EmulationStation adapter and reusable profile-driven implementation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import ClassVar

from retrolibx.core.models import Capabilities, Diagnostic, Game, Library, System
from retrolibx.core.operations import ExportIntent, FileRequest, TextRequest
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.errors import ParseError

from ..base import DetectionResult, ImportResult, LibraryAdapter
from .gamelist import read_gamelist, write_gamelist


class EmulationStationAdapter(LibraryAdapter):
    name = "emulationstation"
    aliases: ClassVar[tuple[str, ...]] = ("es",)
    platform_id = "emulationstation"
    capabilities = Capabilities(artwork=True, video=True, favorites=True, play_stats=True)

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        files = cls._gamelists(path)
        confidence = 0.7 if files else 0.0
        return DetectionResult(
            format=cls.name,
            confidence=confidence,
            evidence=[f"{len(files)} gamelist.xml file(s)"] if files else [],
        )

    @staticmethod
    def _gamelists(path: Path) -> list[Path]:
        if path.is_file() and path.name == "gamelist.xml":
            return [path]
        if not path.is_dir():
            return []
        direct = path / "gamelist.xml"
        if direct.is_file():
            return [direct]
        return sorted(path.glob("*/gamelist.xml"))

    def system_directory(self, system_id: str) -> str | None:
        return self.systems.directory(system_id, self.platform_id) or system_id

    def import_library(self, path: Path, options: ImportOptions) -> ImportResult:
        del options
        root = path if path.is_dir() else path.parent
        systems: list[System] = []
        diagnostics: list[Diagnostic] = []
        for gamelist in self._gamelists(path):
            source_name = gamelist.parent.name
            record = self.systems.resolve(source_name)
            system = System(
                id=record.id if record else source_name,
                name=record.name if record else source_name,
                metadata={self.name: {"directory": source_name}},
            )
            try:
                games, warnings = read_gamelist(gamelist)
            except ParseError as exc:
                diagnostics.append(
                    Diagnostic(
                        severity="error", code="invalid-xml", message=str(exc), path=gamelist
                    )
                )
                continue
            system.games.extend(games)
            diagnostics.extend(
                Diagnostic(
                    severity="warning",
                    code="invalid-game",
                    message=warning,
                    path=gamelist,
                    system_id=system.id,
                )
                for warning in warnings
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
            directory = self.system_directory(system.id)
            if directory is None:
                intent.diagnostics.append(
                    Diagnostic(
                        severity="error",
                        code="unknown-system-mapping",
                        message=f"No {self.name} directory mapping for {system.id}",
                        system_id=system.id,
                    )
                )
                continue
            entries: list[tuple[Game, str, dict[str, str]]] = []
            for game in sorted(system.games, key=lambda item: item.sort_name or item.name):
                if not game.roms:
                    continue
                rom = game.roms[0]
                rom_destination = PurePosixPath(directory) / rom.path.name
                intent.files.append(
                    FileRequest(source=rom.path, destination=rom_destination, category="rom")
                )
                media_paths: dict[str, str] = {}
                for kind, media in game.media.items():
                    media_directory = (
                        "videos" if kind == "video" else "manuals" if kind == "manual" else "images"
                    )
                    media_destination = (
                        PurePosixPath(directory)
                        / media_directory
                        / f"{rom.path.stem}-{kind}{media.suffix or '.png'}"
                    )
                    intent.files.append(
                        FileRequest(source=media, destination=media_destination, category="media")
                    )
                    media_paths[kind] = f"./{media_directory}/{media_destination.name}"
                entries.append((game, f"./{rom.path.name}", media_paths))
                for extra_rom in game.roms[1:]:
                    extra_destination = PurePosixPath(directory) / extra_rom.path.name
                    intent.files.append(
                        FileRequest(
                            source=extra_rom.path, destination=extra_destination, category="rom"
                        )
                    )
            intent.texts.append(
                TextRequest(
                    destination=PurePosixPath(directory) / "gamelist.xml",
                    content=write_gamelist(entries),
                )
            )
        return intent
