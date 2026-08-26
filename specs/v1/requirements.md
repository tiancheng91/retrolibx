# RetroLibX V1 Requirements

## Introduction

RetroLibX V1 is a Python 3.12+ command-line application for migrating complete retro-game libraries between RetroArch, generic EmulationStation, ROCKNIX, ES-DE, and Pegasus. Every conversion passes through a platform-neutral RetroLibX intermediate representation (RLX IR), preserving unsupported source data where practical and keeping source libraries read-only by default.

The repository is currently empty. This specification treats the supplied system design document as the product baseline and covers its complete V1 scope. Online scraping, reference ROM databases, save/BIOS migration, cloud or incremental sync, GUI/Web UI, automatic patching, and duplicate merging are excluded.

## Requirements

### Requirement 1 — Project foundation and developer experience

**User Story:** As a contributor, I want a conventional, typed Python project so that I can install, test, lint, and extend RetroLibX predictably.

#### Acceptance Criteria

1. When the project is installed with Python 3.12 or newer, the package shall expose a `retrolibx` console command.
2. When dependencies are resolved with `uv`, the project shall provide reproducible runtime and development dependency declarations.
3. When quality checks run, the project shall support `pytest`, coverage collection, Ruff, and mypy without requiring undocumented setup.
4. While the application is packaged, the system registry and profile data shall be included as package resources.

### Requirement 2 — Canonical RLX intermediate representation

**User Story:** As an adapter author, I want one canonical data model so that formats never need point-to-point converters.

#### Acceptance Criteria

1. When a library is imported, RetroLibX shall represent it using typed `Library`, `System`, `Game`, `Rom`, `Media`, `Collection`, and `LaunchConfig` models.
2. When model instances are created, mutable collections and mappings shall not be shared between instances.
3. When source fields have no canonical equivalent, RetroLibX shall retain them in namespaced source metadata where practical.
4. When dates, paths, player counts, ratings, favorites, hidden state, and play statistics are present, RetroLibX shall represent them with stable typed values.
5. When a game uses multiple files or discs, RetroLibX shall preserve all ROM entries rather than assuming one game equals one file.

### Requirement 3 — Registry, normalization, and matching

**User Story:** As a user with libraries from different frontends, I want equivalent systems and game names normalized consistently.

#### Acceptance Criteria

1. When a known platform alias, playlist name, directory, or Pegasus name is encountered, RetroLibX shall resolve it to a canonical system ID through a versioned registry.
2. When an unknown system is encountered, RetroLibX shall preserve enough source identity to report and inspect it without silently assigning an incorrect platform.
3. When game matching is requested in V1, RetroLibX shall support exact filename, normalized filename, and playlist-label/title matching in that priority context.
4. When paths and extensions are normalized, RetroLibX shall retain original source values needed for export or diagnostics.

### Requirement 4 — Adapter and profile architecture

**User Story:** As a maintainer, I want formats and platform directory conventions separated so that related platforms can reuse parsers safely.

#### Acceptance Criteria

1. When an adapter is implemented, it shall expose detection, import, export, aliases, and capability metadata through a common interface.
2. When a format is selected, RetroLibX shall resolve it through a registry rather than a chain of format conditionals.
3. When ROCKNIX is processed, RetroLibX shall reuse EmulationStation-compatible data handling and apply a separate ROCKNIX profile.
4. When ES-DE is processed, RetroLibX shall reuse common XML primitives where appropriate while retaining an independent adapter, profile, and media rules.
5. When conversion capabilities differ, RetroLibX shall report material data-loss risks before execution.

### Requirement 5 — RetroArch support

**User Story:** As a RetroArch user, I want playlists and thumbnails migrated without losing launch information.

#### Acceptance Criteria

1. When a directory contains valid RetroArch playlists, the RetroArch adapter shall detect it with a meaningful confidence score.
2. When `.lpl` playlists are imported, RetroLibX shall map labels, ROM paths, CRC values, database names, core names, and core paths into RLX IR.
3. When matching thumbnails exist under `Named_Boxarts`, `Named_Snaps`, or `Named_Titles`, RetroLibX shall map them to semantic media fields.
4. When a RetroArch library is exported, RetroLibX shall emit valid playlists and supported thumbnail paths while preserving representable launch metadata.

### Requirement 6 — EmulationStation-family support

**User Story:** As an EmulationStation, ROCKNIX, or ES-DE user, I want game lists and media migrated according to my platform's conventions.

#### Acceptance Criteria

1. When a valid `gamelist.xml` is present, the generic EmulationStation adapter shall import supported game metadata, ROM paths, and media references.
2. When exporting generic EmulationStation, RetroLibX shall write valid deterministic `gamelist.xml` files without injecting unverified private XML fields.
3. When targeting ROCKNIX, RetroLibX shall map canonical systems to profile-defined directories and write EmulationStation-compatible metadata.
4. When targeting ES-DE, RetroLibX shall apply ES-DE-specific system and media conventions without changing generic EmulationStation behavior.
5. When malformed XML or broken item data is encountered, RetroLibX shall report contextual errors and continue processing independent valid games where safe.

### Requirement 7 — Pegasus support

**User Story:** As a Pegasus user, I want metadata files and launch information converted to and from RLX IR.

#### Acceptance Criteria

1. When `metadata.pegasus.txt` is present, the Pegasus adapter shall detect and parse collections, games, files, supported metadata, and launch directives.
2. When Pegasus metadata is imported, RetroLibX shall associate supported media files through a dedicated media resolver.
3. When a library is exported to Pegasus, RetroLibX shall produce deterministic valid metadata files containing all representable V1 fields.
4. When repeated Pegasus fields or unknown keys are present, RetroLibX shall preserve their meaning or retain them as source metadata where practical.

### Requirement 8 — Conversion planning and safe file operations

**User Story:** As a user migrating a large library, I want to preview and control every filesystem change.

#### Acceptance Criteria

1. When conversion is requested, RetroLibX shall import, normalize, transform, validate, and build a `ConversionPlan` before changing the target filesystem.
2. When dry-run mode is active, RetroLibX shall display planned operations, warnings, conflicts, and summary counts without modifying files.
3. When execution is approved, ROM operations shall support `copy`, `move`, `link`/`symlink`, `hardlink`, and `none`, with `copy` as the default.
4. When execution is approved, media operations shall support `copy`, `hardlink`, and `symlink`, with `copy` as the default.
5. When a target conflict occurs, RetroLibX shall implement `skip`, `overwrite`, `rename`, `error`, and `newer`, with `skip` as the default.
6. While source and target resolve to the same location, RetroLibX shall reject conversion unless an explicit safe in-place mode is selected.
7. While default options are used, RetroLibX shall not delete, overwrite, or modify the source library.
8. When RetroLibX writes a managed target, it shall generate a versioned `.retrolibx/manifest.json` sidecar with source and target format provenance.

### Requirement 9 — CLI workflows and diagnostics

**User Story:** As a command-line user, I want discoverable commands and actionable output for every migration stage.

#### Acceptance Criteria

1. When `detect PATH` runs, RetroLibX shall list the best detected format and confidence or return a clear detection failure.
2. When `scan PATH` runs, RetroLibX shall summarize the imported library and optionally serialize RLX IR as JSON.
3. When `convert SOURCE --to FORMAT --output TARGET` runs, RetroLibX shall auto-detect the source unless `--from` is supplied and then plan or execute the conversion.
4. When `inspect PATH` runs, RetroLibX shall report systems, games, media, and source details useful for diagnosis.
5. When `validate PATH` runs, RetroLibX shall report missing ROMs/media, broken metadata paths, unknown systems, duplicate games, malformed source files, and unsupported extensions where detectable.
6. When a format alias such as `ra`, `es`, or `esde` is supplied, RetroLibX shall resolve it to its canonical adapter.
7. When human output is selected, RetroLibX shall use readable Rich progress and summaries; when JSON logging/output is selected, it shall emit machine-readable structured records.
8. When a single game cannot be parsed or exported, RetroLibX shall report the item-level error and continue independent work unless consistency would be compromised.

### Requirement 10 — Verification and compatibility

**User Story:** As a maintainer, I want fixtures and regression tests proving that adapters preserve library meaning.

#### Acceptance Criteria

1. When the test suite runs, it shall cover import and export for all five V1 formats using isolated fixtures.
2. When an import/export-capable format is round-tripped, tests shall compare game counts, ROM references, supported metadata, media mappings, collections, and launch information.
3. When deterministic text formats are written, golden tests shall cover representative `.lpl`, `gamelist.xml`, and `metadata.pegasus.txt` output.
4. When conversion is dry-run, tests shall prove that no target files are created or modified.
5. When conflict and file modes are exercised, tests shall prove each documented policy and source-safety invariant.

## Product and interface decisions

- Interface: CLI only in V1; no frontend or GUI design work is in scope.
- Runtime: Python 3.12+ with `uv`; Typer, Pydantic, Rich, lxml, and platformdirs are the baseline dependencies.
- Safety: source read-only and target non-overwrite behavior are defaults.
- Architecture: Source → RLX IR → Target; Adapter/Profile and Plan/Execute are strict boundaries.
- Delivery interpretation: “implement the project” means the complete V1 scope above, not the later roadmap.

