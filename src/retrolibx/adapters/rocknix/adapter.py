"""ROCKNIX profile over EmulationStation-compatible metadata."""

from pathlib import Path
from typing import ClassVar

from retrolibx.core.models import Capabilities

from ..base import DetectionResult
from ..emulationstation.adapter import EmulationStationAdapter


class RocknixAdapter(EmulationStationAdapter):
    name = "rocknix"
    aliases: ClassVar[tuple[str, ...]] = ()
    platform_id = "rocknix"
    capabilities = Capabilities(artwork=True, video=True, favorites=True, play_stats=True)

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        gamelists = cls._gamelists(path)
        markers = [path / "roms", path / ".config" / "emulationstation"] if path.is_dir() else []
        rocknix = any(marker.exists() for marker in markers)
        confidence = 0.9 if gamelists and rocknix else 0.0
        return DetectionResult(
            format=cls.name,
            confidence=confidence,
            evidence=["ROCKNIX layout marker", f"{len(gamelists)} gamelist(s)"]
            if confidence
            else [],
        )

    @staticmethod
    def _gamelists(path: Path) -> list[Path]:
        roots = [path / "roms", path] if path.is_dir() else [path]
        for root in roots:
            found = EmulationStationAdapter._gamelists(root)
            if found:
                return found
        return []
