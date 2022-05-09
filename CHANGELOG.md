# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0](releases/tag/v1.0.0) - 2022-05-09

### Changed
- Development, build and release is now based on [python-poetry](https://python-poetry.org).
- No change to functionality since v0.3.0.

### Compatibility
- Python 3.8+

## [0.3.0](releases/tag/v0.3.0) - 2022-01-14

### Added
- Support for globs in Windows, e.g. `sarif summary android*.sarif`
- `info` and `copy` commands

### Compatibility
- Python 3.8+

## [0.2.0](releases/tag/v0.2.0) - 2022-01-07

### Added
- `--blame-filter` argument.

### Changed
- Compatible with Python v3.8.  Previously, Python v3.9 was required.

### Compatibility
- Python 3.8+

## [0.1.0](releases/tag/v0.1.0) - 2021-11-11

### Added
- Initial versions of commands `blame`, `csv`, `diff`, `html`, `ls`, `summary`, `trend`, `usage` and `word` created in Microsoft Global Hackathon 2021.

### Compatibility
- Python 3.9+
