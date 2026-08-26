"""Adapter contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from retrolibx.core.models import Capabilities, Diagnostic, Library
from retrolibx.core.operations import ExportIntent
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.registry import SystemRegistry


class DetectionResult(BaseModel):
    format: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class ImportResult(BaseModel):
    library: Library
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class LibraryAdapter(ABC):
    name: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    capabilities: ClassVar[Capabilities] = Capabilities()

    def __init__(self, systems: SystemRegistry) -> None:
        self.systems = systems

    @classmethod
    @abstractmethod
    def detect(cls, path: Path) -> DetectionResult:
        raise NotImplementedError

    @abstractmethod
    def import_library(self, path: Path, options: ImportOptions) -> ImportResult:
        raise NotImplementedError

    @abstractmethod
    def render_library(
        self, library: Library, target: Path, options: ExportOptions
    ) -> ExportIntent:
        raise NotImplementedError
