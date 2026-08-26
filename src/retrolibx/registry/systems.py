"""Versioned system mapping database."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from retrolibx.core.normalize import normalized_name
from retrolibx.errors import MappingError


class PlatformMapping(BaseModel):
    playlist: list[str] = Field(default_factory=list)
    directory: list[str] = Field(default_factory=list)
    shortname: list[str] = Field(default_factory=list)


class SystemRecord(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    platforms: dict[str, PlatformMapping] = Field(default_factory=dict)


class RegistryDocument(BaseModel):
    version: int
    systems: dict[str, dict[str, object]]


class SystemRegistry:
    def __init__(self, records: dict[str, SystemRecord], version: int = 1) -> None:
        self.records = records
        self.version = version
        self._aliases: dict[str, set[str]] = {}
        for system_id, record in records.items():
            values = [system_id, record.name, *(record.aliases)]
            for mapping in record.platforms.values():
                values.extend(mapping.playlist + mapping.directory + mapping.shortname)
            for value in values:
                self._aliases.setdefault(normalized_name(value), set()).add(system_id)

    @classmethod
    def load(cls, path: Path | None = None) -> SystemRegistry:
        resource = path or Path(str(files("retrolibx.registry").joinpath("systems.yaml")))
        raw = yaml.safe_load(resource.read_text(encoding="utf-8"))
        document = RegistryDocument.model_validate(raw)
        records = {
            system_id: SystemRecord.model_validate({"id": system_id, **data})
            for system_id, data in document.systems.items()
        }
        return cls(records, document.version)

    def resolve(self, value: str) -> SystemRecord | None:
        matches = self._aliases.get(normalized_name(value), set())
        if len(matches) > 1:
            raise MappingError(f"Ambiguous system alias {value!r}: {', '.join(sorted(matches))}")
        return self.records[next(iter(matches))] if matches else None

    def directory(self, system_id: str, platform: str) -> str | None:
        record = self.records.get(system_id)
        if not record:
            return None
        mapping = record.platforms.get(platform)
        return mapping.directory[0] if mapping and mapping.directory else None
