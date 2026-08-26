# RetroLibX

**Universal Retro Game Library Converter**

RetroLibX migrates ROM references, metadata, artwork, videos, collections, and launch settings between RetroArch, generic EmulationStation, ROCKNIX, ES-DE, and Pegasus. All conversions pass through a typed, platform-neutral intermediate representation rather than point-to-point converters.

## Install and run

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync
uv run retrolibx detect /path/to/library
uv run retrolibx scan /path/to/library
uv run retrolibx convert /path/to/source --to rocknix --output /path/to/target --dry-run
uv run retrolibx convert /path/to/source --to rocknix --output /path/to/target
```

The source is read-only by default. ROM modes are `copy`, `move`, `symlink` (`link` alias), `hardlink`, and `none`; media modes are `copy`, `symlink`, and `hardlink`. Conflict policies are `skip`, `overwrite`, `rename`, `error`, and `newer`.

## Commands

- `detect`: rank supported source formats.
- `scan`: import and summarize a library; `--json` outputs RLX IR and `--hash` calculates ROM hashes.
- `convert`: plan and execute a conversion; `--dry-run` never writes.
- `inspect`: show systems, games, ROMs, and media.
- `validate`: report broken paths, unknown systems, duplicates, and malformed metadata.

Aliases: `ra` → `retroarch`, `es` → `emulationstation`, `esde` → `es-de`.

## Development

```bash
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Architecture and acceptance criteria are documented in [`specs/v1`](specs/v1). Adapters implement detection/import/render only. Rendering returns an `ExportIntent`; the planner resolves all conflicts and paths; the executor is the sole filesystem writer.

