"""Library-level validation independent from source syntax."""

from collections import Counter

from retrolibx.registry import SystemRegistry

from .models import Diagnostic, Library
from .normalize import normalized_filename


def validate_library(library: Library, registry: SystemRegistry) -> list[Diagnostic]:
    diagnostics = list(library.diagnostics)
    for system in library.systems:
        if system.id not in registry.records:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="unknown-system",
                    message=f"Unknown canonical system: {system.id}",
                    system_id=system.id,
                )
            )
        names = Counter(normalized_filename(rom.path) for game in system.games for rom in game.roms)
        for game in system.games:
            if not game.roms:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        code="missing-rom-reference",
                        message="Game has no ROM reference",
                        system_id=system.id,
                        game_name=game.name,
                    )
                )
            for rom in game.roms:
                if not rom.path.exists():
                    diagnostics.append(
                        Diagnostic(
                            severity="error",
                            code="missing-rom",
                            message=f"ROM file does not exist: {rom.path}",
                            path=rom.path,
                            system_id=system.id,
                            game_name=game.name,
                        )
                    )
                if names[normalized_filename(rom.path)] > 1:
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="duplicate-rom",
                            message=f"Duplicate normalized ROM filename: {rom.path.name}",
                            path=rom.path,
                            system_id=system.id,
                            game_name=game.name,
                        )
                    )
            for _, media_path in game.media.items():
                if not media_path.exists():
                    diagnostics.append(
                        Diagnostic(
                            severity="warning",
                            code="missing-media",
                            message=f"Media file does not exist: {media_path}",
                            path=media_path,
                            system_id=system.id,
                            game_name=game.name,
                        )
                    )
    return diagnostics
