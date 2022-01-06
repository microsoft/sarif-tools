# SARIF Tools

A set of command line tools and Python library for working with SARIF files.

Read more about the SARIF format here: https://sarifweb.azurewebsites.net/

# Installation

## Prerequisites

You need Python 3.8 or later installed.  Get it from [python.org](https://www.python.org/downloads/).  This document assumes that the `python` command runs that version.

## Installing on Windows

Open an Admin Command Prompt (Start > Command Prompt > Run as Administrator) and type:
```
pip install sarif-tools
```

## Installing on Linux or Mac
```
sudo pip install sarif-tools
```

## Testing the installation

After installing using `pip`, you should then be able to run:
```
sarif --version
```

## Troubleshooting installation

This section has suggestions in case the `sarif` command is not available after installation.

A launcher called `sarif` or `sarif.exe` is created in the Python installation's `Scripts` directory.  The `Scripts` directory needs to be in the `PATH`
environment variable for you to be able to type `sarif` at the command prompt; this is most likely the case if `pip` is run as a
super-user when installing (e.g. Administrator Command Prompt on Windows, or using `sudo` on Linux).

If the `Scripts` directory is not in the `PATH`, then you need to type `python -m sarif` instead of `sarif` to run the tool.

Confusion can arise when the `python` and `pip` commands on the `PATH` are from different installations, or the `python` installation on the super-user's `PATH` is different from the `python` command on the normal user's path.  On Windows, you can use `where python` and `where pip` in normal CMD and Admin CMD to see which installations are in use; on Linux, it's `which python` and `which pip` with and without `sudo`.

# Command Line Usage

```
usage: sarif [-h] [--version] [--debug] [--check {error,warning,note}] {blame,csv,diff,html,ls,summary,trend,usage,word} ...

Process sets of SARIF files

positional arguments:
  {blame,csv,diff,html,ls,summary,trend,usage,word}
                        command

optional arguments:
  -h, --help            show this help message and exit
  --version, -v         show program's version number and exit
  --debug               Print information useful for debugging
  --check {error,warning,note}, -x {error,warning,note}
                        Exit with error code if there are any issues of the specified level (or for diff, an increase in issues at that level).

commands:
  blame       Enhance SARIF file with information from `git blame`
  csv         Write a CSV file listing the issues from the SARIF files(s) specified
  diff        Find the difference between two [sets of] SARIF files
  html        Write a file with HTML representation of SARIF file
  ls          List all SARIF files in the directories specified
  summary     Write a text summary with the counts of issues from the SARIF files(s) specified
  trend       Write a CSV file with time series data from the SARIF file(s) specified, which must
              have timestamps in the filenames in format "yyyymmddThhmmssZ"
  usage       (Command optional) - print usage and exit
  word        Produce MS Word .docx summaries of the SARIF files specified
Run `sarif <COMMAND> --help` for command-specific help.
```

## Commands

The commands are illustrated below assuming input files in the following locations:

- `C:\temp\sarif_files` = a directory of SARIF files with arbitrary filenames.
- `C:\temp\sarif_with_date` = a directory of SARIF files with filenames including timestamps e.g. `C:\temp\sarif_with_date\myapp_devskim_output_20211001T012000Z.sarif`.
- `C:\temp\old_sarif_files` = a directory of SARIF files with arbitrary filenames from an older build.
- `C:\code\my_source_repo` = checkout directory of source code files from which SARIF results were obtained.

### blame
```
usage: sarif blame [-h] [--output PATH] [--code PATH] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output PATH, -o PATH
                        Output file or directory
  --code PATH, -c PATH  Path to git repository; if not specified, the current working directory is used
```

Augment SARIF files with `git blame` information, and write the augmented files to a specified location.
```shell
sarif blame -o "C:\temp\sarif_files_with_blame_info" -c "C:\code\my_source_repo" "C:\temp\sarif_files"
```

If the current working directory is the git repository, the `-c` argument can be omitted.

See [Blame filtering](blame-filtering) below for the format of the blame information that gets added to the SARIF files.

### csv

```
usage: sarif csv [-h] [--output PATH] [--blame-filter FILE] [--autotrim] [--trim PREFIX] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output PATH, -o PATH
                        Output file or directory
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
  --autotrim, -a        Strip off the common prefix of paths in the CSV output
  --trim PREFIX         Prefix to strip from issue paths, e.g. the checkout directory on the build agent
```

Write out a simple tabular list of issues from [a set of] SARIF files.  This can then be analysed, e.g. via Pivot Tables in Excel.

Use the `--trim` option to strip specific prefixes from the paths, to make the CSV less verbose.  Alternatively, use `--autotrim` to strip off the longest common prefix.

Generate a CSV summary of a single SARIF file with common file path prefix suppressed:
```shell
sarif csv "C:\temp\sarif_files\devskim_myapp.sarif"
```

Generate a CSV summary of a directory of SARIF files with path prefix `C:\code\my_source_repo` suppressed:
```shell
sarif csv --trim c:\code\my_source_repo "C:\temp\sarif_files"
```

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

### diff

```
usage: sarif diff [-h] [--output FILE] [--blame-filter FILE] old_file_or_dir new_file_or_dir

positional arguments:
  old_file_or_dir       An old SARIF file or a directory containing the old SARIF files
  new_file_or_dir       A new SARIF file or a directory containing the new SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output FILE, -o FILE
                        Output file
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
```

Print the difference between two [sets of] SARIF files.

Difference between the issues in two SARIF files:
```shell
sarif diff "C:\temp\old_sarif_files\devskim_myapp.sarif" "C:\temp\sarif_files\devskim_myapp.sarif"
```

Difference between the issues in two directories of SARIF files:
```shell
sarif diff "C:\temp\old_sarif_files" "C:\temp\sarif_files"
```

Write output to JSON file instead of printing to stdout:

```shell
sarif diff -o mydiff.json "C:\temp\old_sarif_files\devskim_myapp.sarif" "C:\temp\sarif_files\devskim_myapp.sarif"
```

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

### html

```
usage: sarif html [-h] [--output PATH] [--blame-filter FILE] [--no-autotrim] [--image IMAGE] [--trim PREFIX] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output PATH, -o PATH
                        Output file or directory
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
  --no-autotrim, -n     Do not strip off the common prefix of paths in the output document
  --image IMAGE         Image to include at top of file - SARIF logo by default
  --trim PREFIX         Prefix to strip from issue paths, e.g. the checkout directory on the build agent
```

Create an HTML file summarising SARIF results.

```shell
sarif html -o summary.html "C:\temp\sarif_files"
```

Use the `--trim` option to strip specific prefixes from the paths, to make the generated HTML page less verbose.  The longest common prefix of the paths will be trimmed unless `--no-autotrim` is specified.

Use the `--image` option to provide a header image for the top of the HTML page.  The image is embedded into the HTML, so the HTML document remains a portable standalone file.

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

### ls

```
usage: sarif ls [-h] [--output FILE] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output FILE, -o FILE
                        Output file
```

List SARIF files in one or more directories.

```shell
sarif ls "C:\temp\sarif_files" "C:\temp\sarif_with_date"
```

### summary

```
usage: sarif summary [-h] [--output PATH] [--blame-filter FILE] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output PATH, -o PATH
                        Output file or directory
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
```

Print a summary of the issues in one or more SARIF file(s), grouped by severity and then ordered by number of occurrences.

When directories are provided as input and output, a summary is written for each input file, along with another file containing the totals.

```shell
sarif summary -o summaries "C:\temp\sarif_files"
```

When no output directory or file is specified, the overall summary is printed to the standard output.

```shell
sarif summary "C:\temp\sarif_files\devskim_myapp.sarif"
```

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

### trend

```
usage: sarif trend [-h] [--output FILE] [--blame-filter FILE] [--dateformat {dmy,mdy,ymd}] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output FILE, -o FILE
                        Output file
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
  --dateformat {dmy,mdy,ymd}, -f {dmy,mdy,ymd}
                        Date component order to use in output CSV. Default is `dmy`
```

Generate a CSV showing a timeline of issues from a set of SARIF files in a directory.  The SARIF file names must contain a
timestamp in the specific format `yyyymmddThhhmmss` e.g. `20211012T110000Z`.

The CSV can be loaded in Microsoft Excel for graphing and trend analysis.

```shell
sarif trend -o timeline.csv "C:\temp\sarif_with_date" --dateformat dmy
```

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

### usage

Print usage and exit.

```shell
sarif usage
```

### word

```
usage: sarif word [-h] [--output PATH] [--blame-filter FILE] [--no-autotrim] [--image IMAGE] [--trim PREFIX] [file_or_dir [file_or_dir ...]]

positional arguments:
  file_or_dir           A SARIF file or a directory containing SARIF files

optional arguments:
  -h, --help            show this help message and exit
  --output PATH, -o PATH
                        Output file or directory
  --blame-filter FILE, -b FILE
                        Specify the blame filter file to apply. See README for format.
  --no-autotrim, -n     Do not strip off the common prefix of paths in the output document
  --image IMAGE         Image to include at top of file - SARIF logo by default
  --trim PREFIX         Prefix to strip from issue paths, e.g. the checkout directory on the build agent
```
Create Word documents representing a SARIF file or multiple SARIF files.

If directories are provided for the `-o` option and the input, then a Word document is produced for each individual SARIF file
and for the full set of SARIF files.  Otherwise, a single Word document is created.

Create a Word document for each SARIF file and one for all of them together, in the `reports` directory (created if non-existent):
```shell
sarif word -o reports "C:\temp\sarif_files"
```

Create a Word document for a single SARIF file:
```shell
sarif word -o "reports\devskim_myapp.docx" "C:\temp\sarif_files\devskim_myapp.sarif"
```

Use the `--trim` option to strip specific prefixes from the paths, to make the generated documents less verbose.  The longest common prefix of the paths will be trimmed unless `--no-autotrim` is specified.

Use the `--image` option to provide a header image for the top of the Word document.

See [Blame filtering](blame-filtering) below for how to use the `--blame-filter` option.

# Blame filtering

Use the `sarif blame` command to augment a SARIF file or multiple SARIF files with blame information.

Blame information is added to the property bag of each `result` object for which it was successfully obtained.  The keys and values used are as in the [git blame porcelain format](https://git-scm.com/docs/git-blame#_the_porcelain_format).  E.g.:

```json
{
  "ruleId": "SM00702",
  ...
  "properties": {
    "blame": {
      "author": "aperson",
      "author-mail": "<aperson@acompany.com>",
      "author-time": "1350899798",
      "author-tz": "+0000",
      "committer": "aperson",
      "committer-mail": "<aperson@acompany.com>",
      "committer-time": "1350899798",
      "committer-tz": "+0000",
      "summary": "blah blah commit comment blah",
      "boundary": true,
      "filename": "src/net/myproject/mypackage/MyClass.java"
    }
  }
}
```
Note that the bare `boundary` key is given the automatic value `true`.

This blame data can then be used for filtering and summarising via the `--blame-filter` option available for various commands.  This option requires a path to a filter-list file, containing a list of patterns and substrings to match against the blame information author email.  The format of a filter-list file is as follows:

```
# Lines beginning with # are interpreted as comments and ignored.
# A line beginning with "description: " is interpreted as an optional description for the filter.  If no title is specified, the filter file name is used.
description: Example filter from README.md
# Lines beginning with "+: " are interpreted as inclusion substrings.  E.g. the following line includes issues whose author-mail field contains "@microsoft.com".
+: @microsoft.com
# The "+: " can be omitted.
@microsoft.com
# Instead of a substring, a regular expression can be used, enclosed in "/" characters.  Issues whose author-mail field includes a string matching the regular expression are included.  Use ^ and $ to match the whole author-mail field.
+: /^<myname.*\.com>$/
# Again, the "+: " can be omitted for a regular expression include pattern.
/^<myname.*\.com>$/
# Lines beginning with "-: " are interpreted as exclusion substrings.  E.g. the following line excludes issues whose author-mail field contains "bot@microsoft.com".
-: bot@microsoft.com
# Instead of a substring, a regular expression can be used, enclosed in "/" characters.  Issues whose author-mail field includes a string matching the regular expression are excluded.  Use ^ and $ to match the whole author-mail field.  E.g. the following pattern excludes all issues whose author-mail field contains a GUID.
-: /[0-9A-F]{8}[-][0-9A-F]{4}[-][0-9A-F]{4}[-][0-9A-F]{4}[-][0-9A-F]{12}/
```

Here's an example of a filter-file that includes issues on lines changed by an `@microsoft.com` email address or a `myname.SOMETHING.com` email address, but not if those email addresses end in `bot@microsoft.com` or contain a GUID.  It's the same as the above example, with comments stripped out.

```
description: Example filter from README.md
+: @microsoft.com
+: /^<myname.*\.com>$/
-: bot@microsoft.com
-: /[0-9A-F]{8}[-][0-9A-F]{4}[-][0-9A-F]{4}[-][0-9A-F]{4}[-][0-9A-F]{12}/
```

All matching is case insensitive, because email addresses are.  Whitespace at the start and end of lines is ignored, which also means that line ending characters don't matter.  The blame filter file must be UTF-8 encoded (including plain ASCII7).  It can have a byte order mark or not.

If there are no inclusion patterns, all issues are included except for those matching the exclusion patterns.  If there are inclusion patterns, only issues matching the inclusion patterns are included.  If an issue matches one or more inclusion patterns and also at least one exclusion pattern, it is excluded.

Sometimes, there may be issues in the SARIF file to which the filter cannot be applied, because blame information is not available.  This can be for two reasons: either there is no blame information recorded for the file in which the issue occurred, or the issue location lacks a line number (or specifies line number 1 as a placeholder) so that blame information cannot be correlated to the issue.  These issues are included by default.  To identify which issues these are, create a filter file that excludes everything to which the filter can be applied:

```
description: Exclude everything filterable
-: /.*/
```

Then run a `sarif` command using this filter file as the `--blame-filter` to see the default-included issues.

# Usage as a Python library

Although not its primary purpose, you can use sarif-tools from a Python script or module to
load and summarise SARIF results.

## Basic usage pattern

After installation, use `sarif.loader` to load a SARIF file or files, and then use the operations
on the returned `SarifFile` or `SarifFileSet` objects to explore the data.

```python
from sarif import loader

sarif_data = loader.load_sarif_file(path_to_sarif_file)
issue_count_by_severity = sarif_data.get_result_count_by_severity()
error_histogram = sarif_data.get_issue_code_histogram("error")
```

## Result access API

The three classes defined in the `sarif_files` module, `SarifFileSet`, `SarifFile` and `SarifRun`,
provide similar APIs, which allows SARIF results to be handled similarly at multiple levels of
aggregation.  This section briefly describes some of the key APIs at the three levels of
aggregation.

### get_distinct_tool_names()

Returns a list of distinct tool names in a `SarifFile` or for all files in a `SarifFileSet`.
A `SarifRun` has a single tool name so the equivalent method is `get_tool_name()`.

### get_results()

Return the list of SARIF results.  These are objects as defined in the
[SARIF standard section 3.27](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317638).

### get_records()

Return the list of SARIF results as simplified, flattened record dicts.  Each record has the
attributes defined in `sarif_file.RECORD_ATTRIBUTES`.

- `"Tool"` - the tool name for the run containing the result.
- `"Severity"` - the SARIF severity for the record.  One of `error`, `warning` (the default if the
  record doesn't specify) or `note`.
- `"Code"` - the issue code from the result.
- `"Location"` - the location of the issue, typically the file containing the issue.  Format varies
  by tool.
- `"Line"` - the line number in the file where the issue occurs.  Value is a string.  This defaults
  to `"1"` if the tool failed to identify the line.

### get_records_grouped_by_severity()

As per `get_records()`, but the result is a dict from SARIF severity level (`error`, `warning` and
`note`) to the list of records of that severity level.

### get_result_count(), get_result_count_by_severity()

Get the total number of SARIF results.  `get_result_count_by_severity()` returns a dict from
SARIF severity level (`error`, `warning` and `note`) to the integer number of results of that
severity.

### get_issue_code_histogram(severity)

For the given severity, get histogram in the form of a list of pairs.  The first item in each pair
is the issue code, the second item is the number of matching records, and the list is sorted in
decreasing order of frequency (the same as the `sarif summary` command output).

### Disaggregation and filename access

These fields and methods allow access to the underlying information about the SARIF files.

- `SarifFileSet.subdirs` - a list of `SarifFileSet` objects corresponding to the subdirectories of
  the directory from which the `SarifFileSet` was created.
- `SarifFileSet.files` - a list of `SarifFile` objects corresponding to the SARIF files contained
  in the directory from which the `SarifFileSet` was created.
- `SarifFile.get_abs_file_path()` - get the absolute path to the SARIF file.
- `SarifFile.get_file_name()` - get the name of the SARIF file.
- `SarifFile.get_file_name_without_extension()` - get the name of the SARIF file without its
  extension.  Useful for constructing derived filenames.
- `SarifFile.get_filename_timestamp()` - extract the timestamp from the filename of a SARIF file,
  and return it as a string.  The timestamp must be in the format specified in the `sarif trend`
  command.
- `SarifFile.runs` - a list of `SarifRun` objects contained in the SARIF file.  Most SARIF files
  only contain a single run, but it is possible to aggregate runs from multiple tools into a
  single SARIF file.

### Path shortening API

Call `init_path_prefix_stripping(autotrim, path_prefixes)` on a `SarifFileSet`, `SarifFile` or `SarifRun` object to set up path filtering, either automatically removing the longest common prefix (`autotrim=True`) or removing specific prefixes (`autotrim=False` and a list of strings in `path_prefixes`).

### Blame filtering API

Call `init_blame_filter(filter_description, include_substrings, include_regexes, exclude_substrings, exclude_regexes)` on a `SarifFileSet`, `SarifFile` or `SarifRun` object to set up blame filtering.  `filter_description` is a string and the other parameters are lists of strings (with no `/` characters around the regular expressions).  They correspond in an obvious way to the filter file contents described in [Blame filtering](blame-filtering) above.

Call `get_filter_stats()` to retrieve the filter stats after reading the results or records from sarif files.  It returns `None` if there is no filter, or otherwise a `sarif_file.FilterStats` object with integer fields `filtered_in_result_count`, `filtered_out_result_count`, `missing_blame_count` and `unconvincing_line_number_count`.  Call `to_string()` on the `FilterStats` object for a readable representation of these statistics, which also includes the filter file name or description (`filter_description` field).

# Suggested usage in CI pipelines

Using the `--check` option in combination with the `summary` command causes sarif-tools to exit
with a nonzero exit code if there are any issues of the specified level, or higher.  This can
be useful to fail a continuous integration (CI) pipeline in the case of SAST violation.

The SARIF issue levels are `error`, `warning` and `note`.  These are all valid options for the
`--check` option.

E.g. to fail if there are any errors or warnings:

```
sarif --check warning summary c:\temp\sarif_files
```

The `diff` command can check for any increase in issues of the specified level or above, relative
to a previous or baseline build.

E.g. to fail if there are any new issue codes at error level:

```
sarif --check error diff c:\temp\old_sarif_files c:\temp\sarif_files
```

# Credits

sarif-tools was originally developed during the Microsoft Global Hackathon 2021 by Simon Abykov, Nick Brabbs, Anthony Hayward, Sivaji Kondapalli, Matt Parkes and Kathryn Pentland.
