"""ES-DE profile over shared EmulationStation XML codec."""

from pathlib import Path

from retrolibx.core.models import Capabilities

from ..base import DetectionResult
from ..emulationstation.adapter import EmulationStationAdapter


class ESDEAdapter(EmulationStationAdapter):
    name = "es-de"
    aliases = ("esde",)
    platform_id = "es-de"
    capabilities = Capabilities(
        artwork=True, video=True, collections=True, favorites=True, play_stats=True
    )

    @classmethod
    def detect(cls, path: Path) -> DetectionResult:
        files = cls._gamelists(path)
        marker = path / "ES-DE" if path.is_dir() else path.parent / "ES-DE"
        confidence = 0.92 if files and marker.exists() else 0.0
        return DetectionResult(
            format=cls.name,
            confidence=confidence,
            evidence=["ES-DE marker", f"{len(files)} gamelist(s)"] if confidence else [],
        )
