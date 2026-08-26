"""RetroLibX command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from retrolibx import __version__
from retrolibx.application import ConversionService
from retrolibx.core.models import Diagnostic, Library
from retrolibx.core.operations import ConversionPlan
from retrolibx.core.options import ConflictPolicy, ExportOptions, ImportOptions, MediaMode, RomMode
from retrolibx.errors import (
    ConflictError,
    DetectionError,
    ParseError,
    RetroLibXError,
    ValidationError,
)

app = typer.Typer(
    help="Universal Retro Game Library Converter",
    no_args_is_help=True,
    invoke_without_command=True,
)
console = Console()
error_console = Console(stderr=True)


def _json(value: object) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2))


def _library_table(library: Library) -> Table:
    table = Table(title=f"{library.format} library")
    table.add_column("System")
    table.add_column("Games", justify="right")
    table.add_column("Media", justify="right")
    for system in library.systems:
        table.add_row(
            system.name,
            str(len(system.games)),
            str(sum(len(game.media.items()) for game in system.games)),
        )
    table.add_section()
    table.add_row("Total", str(library.game_count), str(library.media_count))
    return table


def _diagnostics(items: list[Diagnostic]) -> None:
    for item in items:
        style = (
            "red" if item.severity == "error" else "yellow" if item.severity == "warning" else "dim"
        )
        error_console.print(
            f"[{style}]{item.severity.upper()}[/{style}] {item.code}: {item.message}"
        )


def _plan_table(plan: ConversionPlan) -> Table:
    table = Table(title="Conversion plan")
    table.add_column("Operation")
    table.add_column("Count", justify="right")
    counts: dict[str, int] = {}
    for operation in plan.operations:
        key = operation.kind + (" (skipped)" if getattr(operation, "skipped", False) else "")
        counts[key] = counts.get(key, 0) + 1
    for key, value in sorted(counts.items()):
        table.add_row(key, str(value))
    return table


@app.callback()
def main(
    version: Annotated[bool | None, typer.Option("--version", help="Show version")] = None,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def detect(path: Path, json_output: Annotated[bool, typer.Option("--json")] = False) -> None:
    results = ConversionService().detect(path)
    if not results:
        raise DetectionError(f"Could not detect a supported library at {path}")
    if json_output:
        _json([result.model_dump(mode="json") for result in results])
        return
    table = Table(title="Detection results")
    table.add_column("Format")
    table.add_column("Confidence", justify="right")
    table.add_column("Evidence")
    for result in results:
        table.add_row(result.format, f"{result.confidence:.0%}", "; ".join(result.evidence))
    console.print(table)


@app.command()
def scan(
    path: Path,
    source_format: Annotated[str | None, typer.Option("--from")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    calculate_hashes: Annotated[bool, typer.Option("--hash")] = False,
) -> None:
    _, library = ConversionService().import_library(
        path, source_format, ImportOptions(calculate_hashes=calculate_hashes)
    )
    if json_output:
        _json(library)
    else:
        console.print(_library_table(library))
        _diagnostics(library.diagnostics)


@app.command("inspect")
def inspect_command(
    path: Path,
    source_format: Annotated[str | None, typer.Option("--from")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _, library = ConversionService().import_library(path, source_format)
    if json_output:
        _json(library)
    else:
        console.print(_library_table(library))
        for system in library.systems:
            console.print(f"[bold]{system.name}[/bold] ({system.id})")
            for game in system.games:
                console.print(
                    f"  {game.name} — {len(game.roms)} ROM(s), {len(game.media.items())} media"
                )
        _diagnostics(library.diagnostics)


@app.command()
def validate(
    path: Path,
    source_format: Annotated[str | None, typer.Option("--from")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _, library = ConversionService().import_library(path, source_format)
    if json_output:
        _json(library.diagnostics)
    else:
        _diagnostics(library.diagnostics)
        errors = sum(item.severity == "error" for item in library.diagnostics)
        console.print(
            f"Validation complete: {errors} error(s), {len(library.diagnostics) - errors} other diagnostic(s)"
        )
    if any(item.severity == "error" for item in library.diagnostics):
        raise typer.Exit(1)


@app.command()
def convert(
    source: Path,
    target_format: Annotated[str, typer.Option("--to")],
    output: Annotated[Path, typer.Option("--output")],
    source_format: Annotated[str | None, typer.Option("--from")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    rom_mode: Annotated[RomMode, typer.Option("--rom-mode")] = RomMode.COPY,
    media_mode: Annotated[MediaMode, typer.Option("--media-mode")] = MediaMode.COPY,
    conflict: Annotated[ConflictPolicy, typer.Option("--conflict")] = ConflictPolicy.SKIP,
    in_place: Annotated[bool, typer.Option("--in-place")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    result = ConversionService().convert(
        source,
        output,
        target_format,
        source_format=source_format,
        export_options=ExportOptions(
            rom_mode=rom_mode, media_mode=media_mode, conflict=conflict, in_place=in_place
        ),
        dry_run=dry_run,
    )
    if json_output:
        _json(result)
        return
    console.print(_library_table(result.library))
    console.print(_plan_table(result.plan))
    _diagnostics(result.plan.diagnostics)
    if dry_run:
        console.print("[bold]Dry run:[/bold] no files changed")
    elif result.execution:
        console.print(
            f"Completed {len(result.execution.completed)} operation(s); skipped {len(result.execution.skipped)}"
        )


def run() -> None:
    try:
        app()
    except (DetectionError, ParseError) as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(3) from exc
    except (ConflictError, ValidationError) as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(4) from exc
    except RetroLibXError as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    run()
