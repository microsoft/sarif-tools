# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.4] - 2024-11-15

- #73 Crash when using `--check`.

## [3.0.3] - 2024-09-30

- #43 Support getting level from `ruleConfigurationOverrides` and `defaultConfiguration`.
- #68 Fixed regression where reversing diff direction gave different results.

## [3.0.2] - 2024-09-18

- #55 part 2: Add `executionSuccessful` to `copy` operation output for SARIF schema compliance.

## [3.0.1] - 2024-09-16

### Fixed

- #58 Fixed regression that broke `sarif diff` command in v3.0.0.

## [3.0.0](releases/tag/v3.0.0) - 2024-09-10

### Breaking Changes

- Changed Python API to use new IssueReport type for issue grouping and sorting:
  - `SarifFileSet` now has a `get_report()` method
  - `s.get_result_count_by_severity()` replaced by
    `s.get_report().get_issue_type_histogram_for_severity(severity)`
  - `s.get_result_count_by_severity()` replaced by
    `s.get_report().get_issue_count_for_severity(severity)`
  - `s.get_records_grouped_by_severity()` replaced by
    `s.get_report().get_issues_for_severity(severity)`

### Added

- Support "none" severity level. It's only included in the output if present in the input.

### Fixed

- #39 Truncate long summaries.
- Made issue sorting and grouping more consistent across the various reports.
- Multiple occurrences of a single issue are now sorted by location in the Word report.
- Improved debug and version reporting for when multiple versions are installed.
- For the copy operation, "invocation" in the resulting sarif is changed to an object to match the spec.
- #53 Fix the `blame` command for `file:///` URL locations.

### Compatibility

- Python 3.8+

## [2.0.0](releases/tag/v2.0.0) - 2022-11-07

### Breaking Changes

- "Code" and "Description" are now separate columns in the CSV output, whereas before they were
  combined in the "Code" column. They are also separate keys in the "record" format if calling
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

- Compatible with Python v3.8. Previously, Python v3.9 was required.

### Compatibility

- Python 3.8+

## [0.1.0](releases/tag/v0.1.0) - 2021-11-11

### Added

- Initial versions of commands `blame`, `csv`, `diff`, `html`, `ls`, `summary`, `trend`, `usage` and `word` created in Microsoft Global Hackathon 2021.

### Compatibility

- Python 3.9+
