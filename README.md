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

## Repository discovery

RetroLibX does not require one fixed repository layout. It recursively discovers `.lpl`,
`gamelist.xml`, and `metadata.pegasus.txt` below the supplied source root (excluding tool and
VCS directories). Referenced ROM and media paths are resolved in this order:

1. an existing absolute path;
2. a path relative to the metadata file or detected frontend root;
3. a path relative to the supplied repository root;
4. a unique trailing-path match, which handles stale device roots such as `/storage/roms`;
5. a unique filename match, with semantic directory hints for ROMs, covers, screenshots,
   videos, and manuals.

Ambiguous filename matches are intentionally left unresolved and reported by validation instead
of silently selecting the wrong game or artwork.

## Development

```bash
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Architecture and acceptance criteria are documented in [`specs/v1`](specs/v1). Adapters implement detection/import/render only. Rendering returns an `ExportIntent`; the planner resolves all conflicts and paths; the executor is the sole filesystem writer.
