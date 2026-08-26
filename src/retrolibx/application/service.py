"""Use-case orchestration shared by CLI and future integrations."""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

from pydantic import BaseModel

from retrolibx.adapters import AdapterRegistry, builtin_registry
from retrolibx.adapters.base import DetectionResult, LibraryAdapter
from retrolibx.core.executor import PlanExecutor
from retrolibx.core.models import Diagnostic, Library
from retrolibx.core.operations import ConversionPlan, ExecutionReport
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.core.planner import ConversionPlanner
from retrolibx.core.validation import validate_library


class ConversionResult(BaseModel):
    library: Library
    plan: ConversionPlan
    execution: ExecutionReport | None = None


class ConversionService:
    def __init__(
        self,
        adapters: AdapterRegistry | None = None,
        planner: ConversionPlanner | None = None,
        executor: PlanExecutor | None = None,
    ) -> None:
        self.adapters = adapters or builtin_registry()
        self.planner = planner or ConversionPlanner()
        self.executor = executor or PlanExecutor()

    def detect(self, path: Path) -> list[DetectionResult]:
        return [result for result in self.adapters.detect_all(path) if result.confidence > 0]

    def import_library(
        self, path: Path, source_format: str | None = None, options: ImportOptions | None = None
    ) -> tuple[LibraryAdapter, Library]:
        adapter = (
            self.adapters.resolve(source_format) if source_format else self.adapters.detect(path)[0]
        )
        import_options = options or ImportOptions()
        result = adapter.import_library(path, import_options)
        library = result.library
        if import_options.calculate_hashes:
            self._calculate_hashes(library)
        library.diagnostics = validate_library(library, self.adapters.systems)
        return adapter, library

    def convert(
        self,
        source: Path,
        target: Path,
        target_format: str,
        *,
        source_format: str | None = None,
        import_options: ImportOptions | None = None,
        export_options: ExportOptions | None = None,
        dry_run: bool = False,
    ) -> ConversionResult:
        source_adapter, library = self.import_library(source, source_format, import_options)
        target_adapter = self.adapters.resolve(target_format)
        options = export_options or ExportOptions()
        intent = target_adapter.render_library(library, target, options)
        intent.diagnostics.extend(self._loss_report(source_adapter, target_adapter, library))
        plan = self.planner.plan(
            intent,
            source_root=source,
            target_root=target,
            source_format=source_adapter.name,
            target_format=target_adapter.name,
            options=options,
        )
        execution = None if dry_run else self.executor.execute(plan)
        return ConversionResult(library=library, plan=plan, execution=execution)

    @staticmethod
    def _calculate_hashes(library: Library) -> None:
        for system in library.systems:
            for game in system.games:
                for rom in game.roms:
                    if not rom.path.is_file():
                        continue
                    crc = 0
                    md5 = hashlib.md5(usedforsecurity=False)
                    sha1 = hashlib.sha1(usedforsecurity=False)
                    size = 0
                    with rom.path.open("rb") as handle:
                        while chunk := handle.read(1024 * 1024):
                            size += len(chunk)
                            crc = zlib.crc32(chunk, crc)
                            md5.update(chunk)
                            sha1.update(chunk)
                    rom.size = size
                    rom.crc32 = f"{crc & 0xFFFFFFFF:08X}"
                    rom.md5 = md5.hexdigest()
                    rom.sha1 = sha1.hexdigest()

    @staticmethod
    def _loss_report(
        source: LibraryAdapter, target: LibraryAdapter, library: Library
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        labels = {
            "video": "video assets",
            "collections": "collections",
            "favorites": "favorite flags",
            "play_stats": "play statistics",
            "launch_config": "launch configuration",
        }
        for field, label in labels.items():
            if getattr(source.capabilities, field) and not getattr(target.capabilities, field):
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        code="potential-data-loss",
                        message=f"Target {target.name} cannot fully represent {label}",
                        details={"field": field},
                    )
                )
        if library.collections and not target.capabilities.collections:
            diagnostics.append(
                Diagnostic(
                    severity="warning",
                    code="potential-data-loss",
                    message=f"Target {target.name} does not support collections",
                )
            )
        return diagnostics
