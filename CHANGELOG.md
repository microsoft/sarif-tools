# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0](releases/tag/v2.1.0) - Unreleased

### Fixed

- #39 Truncate long summaries.

### Compatibility

- Python 3.8+

## [2.0.0](releases/tag/v2.0.0) - 2022-11-07

### Breaking Changes

- "Code" and "Description" are now separate columns in the CSV output, whereas before they were
  combined in the "Code" column.  They are also separate keys in the "record" format if calling
  sarif-tools from Python.
- `--blame-filter` argument has been replaced with `--filter`, using a new YAML-based format for
  more general filtering to replace the previous ad hoc text format which only supported blame.
  - There is a new `upgrade-filter` command to upgrade your old blame filter files to the new
    format.
  - Thanks to @abyss638 for contributing this enhancement!

### Added

- New `codeclimate` command to generate output for GitLab use.
  - Thanks to @abyss638 for contributing this enhancement!
- New `emacs` command to generate output for the popular Linux text editor.
  - Thanks to @dkloper for contributing this enhancement!
- #14 Support recursive glob
  - Thanks to @bushelofsilicon for contributing this enhancement!

### Changed

- When an input SARIF file contains blame information, the `csv` command output now has a column
  for `Author`.
- #18 The `diff` command now prints up to three locations of new occurrences of issues (all are
  listed in the file output mode).

### Fixed

- #4 and #19 docs improvements.
- #12 allow zero locations for record.
- #15 allow `text` to be absent in `message` object.
- #20 allow UTF8 with BOM (`utf-8-sig`` encoding)
  - Thanks to @ManuelBerrueta for contributing this fix!

### Compatibility

- Python 3.8+

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
