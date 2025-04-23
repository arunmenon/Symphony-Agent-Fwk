# Symphony Core Changelog

All notable changes to the Symphony Core framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0a1] - 2025-04-24

### Added
- Complete P0 API stabilization
- API barrel file in `symphony/api.py` with all public exports
- `@api_stable` decorator for tracking API stability
- Contract tests for API compatibility
- Minimal DAG example
- Python 3.11 support
- Public API surface inventory in `docs/public_surface.md`
- CI workflow for contract tests

### Changed
- Package name changed to `symphony-core`
- Build system migrated to Hatchling

### Fixed
- Proper metadata in pyproject.toml

## [0.0.1] - 2025-04-01

### Added
- Initial internal development release