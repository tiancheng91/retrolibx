# RetroLibX V1 Implementation Plan

- [x] 1. Bootstrap the Python project
  - Add `pyproject.toml`, package metadata, CLI entry point, dependency and tool configuration.
  - Create the source/test directory structure and basic documentation.
  - _Requirements: 1, 9_

- [x] 2. Implement the domain and diagnostic foundation
  - Implement RLX IR, options, capabilities, diagnostics, errors, serialization, and normalization.
  - Implement the versioned canonical system registry and packaged YAML data.
  - _Requirements: 2, 3, 4_

- [x] 3. Implement planning and safe execution
  - Implement export intents, typed operations, conflict handling, containment checks, dry-run plans, executor, and manifest.
  - Cover ROM/media modes and source-safety invariants.
  - _Requirements: 8_

- [x] 4. Implement RetroArch and ROCKNIX vertical slice
  - Implement RetroArch detection, playlist/media import and export.
  - Implement reusable EmulationStation XML primitives and ROCKNIX profile/adapter.
  - Add MVP integration fixtures and tests.
  - _Requirements: 4, 5, 6, 10_

- [x] 5. Implement remaining V1 adapters
  - Implement generic EmulationStation, ES-DE, and Pegasus detection/import/export/media rules.
  - Add adapter contract, golden, and semantic round-trip tests.
  - _Requirements: 4, 6, 7, 10_

- [x] 6. Implement the application service and CLI
  - Implement detect, scan, convert, inspect, and validate workflows.
  - Add Rich human output, JSON output, aliases, stable errors, and data-loss reporting.
  - _Requirements: 4, 8, 9_

- [x] 7. Complete verification and documentation
  - Run and fix pytest with coverage, Ruff formatting/linting, and strict mypy.
  - Verify dry-run, source safety, conflicts, format round trips, and end-to-end conversion.
  - Complete README usage and extension documentation.
  - _Requirements: 1, 10_
