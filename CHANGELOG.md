# Changelog

All notable changes to RetroLibX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-27

### Added

- Introduced the typed RetroLibX intermediate representation (RLX IR) for libraries, systems,
  games, multi-file ROMs, semantic media, collections, launch configuration, and diagnostics.
- Added detection, import, and export support for RetroArch, generic EmulationStation, ROCKNIX,
  ES-DE, and Pegasus libraries.
- Added the `detect`, `scan`, `convert`, `inspect`, and `validate` CLI commands with Rich output
  and machine-readable JSON modes.
- Added a versioned canonical system registry for platform aliases, ROM extensions, playlist
  names, target directories, and Pegasus short names.
- Added recursive discovery for `.lpl`, `gamelist.xml`, and `metadata.pegasus.txt` files across
  repositories with non-standard directory layouts.
- Added repository-wide ROM and media resolution using direct paths, metadata-relative paths,
  repository-relative paths, trailing-path matching, and unambiguous filename fallback.
- Added `--game-name-field` to read game titles from non-standard RetroArch playlist fields while
  retaining the original `label` for thumbnail matching.
- Added conversion planning with dry-run reports, conflict policies (`skip`, `overwrite`,
  `rename`, `error`, and `newer`), and configurable ROM and media transfer modes.
- Added versioned `.retrolibx/manifest.json` output containing conversion provenance and selected
  file policies.
- Added adapter capability declarations and data-loss diagnostics when a target format cannot
  represent source metadata.
- Added opt-in CRC32, MD5, and SHA-1 ROM hashing with `scan --hash`.
- Added unit, adapter, round-trip, safety, CLI, and end-to-end tests with an 80% coverage gate.
- Added GitHub Actions checks for pytest, Ruff, formatting, strict mypy, and package builds.
- Added trusted PyPI publishing for matching `v*` tags, including tag/package version validation.
- Added project artwork, repository guidance for coding agents, and MIT licensing.

### Changed

- Separated format adapters from platform profiles so ROCKNIX and ES-DE can reuse
  EmulationStation XML primitives without inheriting platform-specific behavior.
- Separated adapter rendering, conversion planning, and filesystem execution so adapters remain
  side-effect free and dry-run never writes target files.
- Standardized resolved IR paths as absolute `Path` values without requiring source metadata to
  use absolute or currently valid device paths.
- Made metadata writers deterministic through stable system, game, field, and path ordering.

### Fixed

- Fixed RetroArch detection when `retroarch/playlists` is nested below a game collection root.
- Fixed ROM lookup for playlists containing stale device paths such as `/storage/roms/...` or
  `/ROM/...` when the files exist elsewhere in the supplied repository.
- Fixed thumbnail lookup for repositories that store artwork outside the conventional RetroArch
  directory while preserving semantic distinctions between box art, screenshots, and titles.
- Fixed Hatch package configuration so wheel and source distributions include the complete Python
  package as well as the system registry and license.

### Security

- Kept source libraries read-only by default and rejected source/target path equality unless
  explicitly allowed.
- Constrained every planned and executed destination to the selected target root and rechecked
  filesystem state immediately before writes.
- Disabled XML network access, DTD loading, and external entity resolution.
- Used atomic metadata writes and wrote the RetroLibX manifest only after preceding operations
  completed.
- Treated imported launch commands as metadata only; RetroLibX never executes them.

[Unreleased]: https://github.com/tiancheng91/RetroLibX/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tiancheng91/RetroLibX/releases/tag/v0.1.0

