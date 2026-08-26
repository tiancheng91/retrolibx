"""The only component authorized to apply a ConversionPlan."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from retrolibx.errors import FileOperationError

from .operations import (
    ConversionPlan,
    CreateDirectory,
    ExecutionReport,
    TransferFile,
    WriteManifest,
    WriteText,
)
from .options import MediaMode, RomMode


class PlanExecutor:
    def execute(self, plan: ConversionPlan) -> ExecutionReport:
        report = ExecutionReport()
        for operation in plan.operations:
            destination = operation.destination
            try:
                self._assert_contained(plan.target_root, destination)
                if getattr(operation, "skipped", False):
                    report.skipped.append(destination)
                    continue
                if isinstance(operation, CreateDirectory):
                    destination.mkdir(parents=True, exist_ok=True)
                elif isinstance(operation, TransferFile):
                    self._transfer(operation)
                elif isinstance(operation, (WriteText, WriteManifest)):
                    self._write_text(destination, operation.content, operation.overwrite)
                report.completed.append(destination)
            except (OSError, FileOperationError) as exc:
                raise FileOperationError(f"Failed operation at {destination}: {exc}") from exc
        return report

    @staticmethod
    def _assert_contained(root: Path, destination: Path) -> None:
        try:
            destination.resolve(strict=False).relative_to(root.resolve(strict=False))
        except ValueError as exc:
            raise FileOperationError(f"Destination escaped target root: {destination}") from exc

    @staticmethod
    def _prepare(destination: Path, overwrite: bool) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            if not overwrite:
                raise FileOperationError(f"Target changed after planning: {destination}")
            if destination.is_dir() and not destination.is_symlink():
                raise FileOperationError(f"Cannot overwrite directory: {destination}")
            destination.unlink()

    def _transfer(self, operation: TransferFile) -> None:
        if not operation.source.is_file():
            raise FileOperationError(f"Source file is missing: {operation.source}")
        self._prepare(operation.destination, operation.overwrite)
        if operation.mode in {RomMode.COPY, MediaMode.COPY}:
            shutil.copy2(operation.source, operation.destination)
        elif operation.mode == RomMode.MOVE:
            shutil.move(operation.source, operation.destination)
        elif operation.mode in {RomMode.SYMLINK, MediaMode.SYMLINK}:
            os.symlink(operation.source.resolve(), operation.destination)
        elif operation.mode in {RomMode.HARDLINK, MediaMode.HARDLINK}:
            os.link(operation.source, operation.destination)
        else:
            raise FileOperationError(f"Unsupported transfer mode: {operation.mode}")

    def _write_text(self, destination: Path, content: str, overwrite: bool) -> None:
        self._prepare(destination, overwrite)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
