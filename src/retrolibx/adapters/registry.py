"""Adapter registration, aliases, and detection."""

from __future__ import annotations

from pathlib import Path

from retrolibx.errors import DetectionError
from retrolibx.registry import SystemRegistry

from .base import DetectionResult, LibraryAdapter


class AdapterRegistry:
    def __init__(self, systems: SystemRegistry) -> None:
        self.systems = systems
        self._classes: dict[str, type[LibraryAdapter]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, adapter: type[LibraryAdapter]) -> None:
        if adapter.name in self._classes:
            raise ValueError(f"Duplicate adapter: {adapter.name}")
        self._classes[adapter.name] = adapter
        for alias in (adapter.name, *adapter.aliases):
            key = alias.casefold()
            if key in self._aliases:
                raise ValueError(f"Duplicate adapter alias: {alias}")
            self._aliases[key] = adapter.name

    def resolve(self, value: str) -> LibraryAdapter:
        canonical = self._aliases.get(value.casefold())
        if canonical is None:
            supported = ", ".join(sorted(self._classes))
            raise DetectionError(f"Unknown format {value!r}; supported: {supported}")
        return self._classes[canonical](self.systems)

    def detect_all(self, path: Path) -> list[DetectionResult]:
        return sorted(
            (adapter.detect(path) for adapter in self._classes.values()),
            key=lambda item: (-item.confidence, item.format),
        )

    def detect(self, path: Path) -> tuple[LibraryAdapter, DetectionResult]:
        candidates = [result for result in self.detect_all(path) if result.confidence > 0]
        if not candidates:
            raise DetectionError(f"Could not detect a supported library at {path}")
        best = candidates[0]
        tied = [item for item in candidates if item.confidence == best.confidence]
        if len(tied) > 1:
            names = ", ".join(item.format for item in tied)
            raise DetectionError(f"Ambiguous library format ({names}); specify --from")
        return self.resolve(best.format), best


def builtin_registry(systems: SystemRegistry | None = None) -> AdapterRegistry:
    from .emulationstation.adapter import EmulationStationAdapter
    from .esde.adapter import ESDEAdapter
    from .pegasus.adapter import PegasusAdapter
    from .retroarch.adapter import RetroArchAdapter
    from .rocknix.adapter import RocknixAdapter

    registry = AdapterRegistry(systems or SystemRegistry.load())
    for adapter in (
        RetroArchAdapter,
        EmulationStationAdapter,
        RocknixAdapter,
        ESDEAdapter,
        PegasusAdapter,
    ):
        registry.register(adapter)
    return registry
