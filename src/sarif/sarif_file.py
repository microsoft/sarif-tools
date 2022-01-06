"""
Defines classes representing sets of SARIF files, individual SARIF files and runs within SARIF
files, along with associated functions and constants.
"""

import copy
import os
import re
from typing import Dict, Iterator, List, Optional, Tuple

SARIF_SEVERITIES = ["error", "warning", "note"]

RECORD_ATTRIBUTES = ["Tool", "Severity", "Code", "Location", "Line"]

# Standard time format, e.g. `20211012T110000Z` (not part of the SARIF standard).
# Can obtain from bash via `date +"%Y%m%dT%H%M%SZ"``
DATETIME_REGEX = r"\d{8}T\d{6}Z"

_SLASHES = ["\\", "/"]


def has_sarif_file_extension(filename):
    """
    As per section 3.2 of the SARIF standard, SARIF filenames SHOULD end in ".sarif" and MAY end in
    ".sarif.json".
    https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317421
    """
    filename_upper = filename.upper().strip()
    return any(filename_upper.endswith(x) for x in [".SARIF", ".SARIF.JSON"])


def _read_result_location(result) -> Tuple[str, str]:
    """
    Extract the file path and line number strings from the Result.
    Tools store this in different ways, so this function tries a few different JSON locations.
    """
    file_path = None
    line_number = None
    locations = result.get("locations", [])
    if locations:
        location = locations[0]
        physical_location = location.get("physicalLocation", {})
        # SpotBugs has some errors with no line number so deal with them by just leaving it at 1
        line_number = physical_location.get("region", {}).get("startLine", None)
        # For file name, first try the location written by DevSkim
        file_path = (
            location.get("physicalLocation", {})
            .get("address", {})
            .get("fullyQualifiedName", None)
        )
        if not file_path:
            # Next try the physical location written by MobSF and by SpotBugs (for some errors)
            file_path = (
                location.get("physicalLocation", {})
                .get("artifactLocation", {})
                .get("uri", None)
            )
        if not file_path:
            logical_locations = location.get("logicalLocations", None)
            if logical_locations:
                # Finally, try the logical location written by SpotBugs for some errors
                file_path = logical_locations[0].get("fullyQualifiedName", None)
    return (file_path, line_number)


def _group_records_by_severity(records) -> Dict[str, List[Dict]]:
    """
    Get the records, grouped by severity.
    """
    return {
        severity: [record for record in records if record["Severity"] == severity]
        for severity in SARIF_SEVERITIES
    }


def _count_records_by_issue_code(records, severity) -> List[Tuple]:
    """
    Return a list of pairs (code, count) of the records with the specified
    severities.
    """
    code_to_count = {}
    for record in records:
        if record["Severity"] == severity:
            code = record["Code"]
            code_to_count[code] = code_to_count.get(code, 0) + 1
    return sorted(code_to_count.items(), key=lambda x: x[1], reverse=True)


class FilterStats:
    """
    Statistics that record the outcome of a a filter.
    """

    def __init__(self, filter_description):
        self.filter_description = filter_description
        self.reset_counters()

    def reset_counters(self):
        """
        Zero all the counters.
        """
        self.filtered_in_result_count = 0
        self.filtered_out_result_count = 0
        self.missing_blame_count = 0
        self.unconvincing_line_number_count = 0

    def add(self, other_filter_stats):
        """
        Add another set of filter stats to my totals.
        """
        if other_filter_stats:
            if other_filter_stats.filter_description and (
                other_filter_stats.filter_description != self.filter_description
            ):
                self.filter_description += f", {other_filter_stats.filter_description}"
            self.filtered_in_result_count += other_filter_stats.filtered_in_result_count
            self.filtered_out_result_count += (
                other_filter_stats.filtered_out_result_count
            )
            self.missing_blame_count += other_filter_stats.missing_blame_count
            self.unconvincing_line_number_count += (
                other_filter_stats.unconvincing_line_number_count
            )

    def __str__(self):
        """
        Automatic to_string()
        """
        return self.to_string()

    def to_string(self):
        """
        Generate a summary string for these filter stats.
        """
        ret = (
            f"'{self.filter_description}': "
            f"{self.filtered_out_result_count} filtered out, "
            f"{self.filtered_in_result_count} passed the filter"
        )
        if self.unconvincing_line_number_count:
            ret += (
                f", {self.unconvincing_line_number_count} included by default "
                "for lacking line number information"
            )
        if self.missing_blame_count:
            ret += (
                f", {self.missing_blame_count} included by default "
                "for lacking the blame data required for filtering"
            )
        return ret


def _add_filter_stats(accumulator, filter_stats):
    if filter_stats:
        if accumulator:
            accumulator.add(filter_stats)
            return accumulator
        return copy.copy(filter_stats)
    return accumulator


class _BlameFilter:
    """
    Class that implements blame filtering.
    """

    def __init__(self):
        self.filter_stats = None
        self.include_substrings = None
        self.include_regexes = None
        self.apply_inclusion_filter = False
        self.exclude_substrings = None
        self.exclude_regexes = None
        self.apply_exclusion_filter = False

    def init_blame_filter(
        self,
        filter_description,
        include_substrings,
        include_regexes,
        exclude_substrings,
        exclude_regexes,
    ):
        """
        Initialise the blame filter with the given filter patterns.
        """
        self.filter_stats = FilterStats(filter_description)
        self.include_substrings = (
            [s.upper().strip() for s in include_substrings]
            if include_substrings
            else None
        )
        self.include_regexes = include_regexes[:] if include_regexes else None
        self.apply_inclusion_filter = bool(
            self.include_substrings or self.include_regexes
        )
        self.exclude_substrings = (
            [s.upper().strip() for s in exclude_substrings]
            if exclude_substrings
            else None
        )
        self.exclude_regexes = exclude_regexes[:] if exclude_regexes else None
        self.apply_exclusion_filter = bool(
            self.exclude_substrings or self.exclude_regexes
        )

    def _zero_counts(self):
        if self.filter_stats:
            self.filter_stats.reset_counters()

    def _check_include_result(self, author_mail):
        author_mail_upper = author_mail.upper().strip()
        if self.apply_inclusion_filter:
            matches_an_include_substring = self.include_substrings and any(
                s in author_mail_upper for s in self.include_substrings
            )
            matches_an_include_regexp = self.include_regexes and any(
                re.search(r, author_mail, re.IGNORECASE) for r in self.include_regexes
            )
            if (not matches_an_include_substring) and (not matches_an_include_regexp):
                return False
        if self.exclude_substrings and any(
            s in author_mail_upper for s in self.exclude_substrings
        ):
            return False
        if self.exclude_regexes and any(
            re.search(r, author_mail, re.IGNORECASE) for r in self.exclude_regexes
        ):
            return False
        return True

    def _filter_append(self, filtered_results, result, blame_info):
        if blame_info:
            author_mail = blame_info.get("author-mail", None) or blame_info.get(
                "committer-mail", None
            )
            if author_mail:
                # First, check inclusion
                if self._check_include_result(author_mail):
                    self.filter_stats.filtered_in_result_count += 1
                    filtered_results.append(result)
                else:
                    (_file_path, line_number) = _read_result_location(result)
                    if line_number == "1" or not line_number:
                        # Line number is not convincing.  Blame information may be misattributed.
                        self.filter_stats.unconvincing_line_number_count += 1
                        filtered_results.append(result)
                    else:
                        self.filter_stats.filtered_out_result_count += 1
            else:
                self.filter_stats.missing_blame_count += 1
                # Result did not contain complete blame information, so don't filter it out.
                filtered_results.append(result)
        else:
            self.filter_stats.missing_blame_count += 1
            # Result did not contain blame information, so don't filter it out.
            filtered_results.append(result)

    def filter_results(self, results):
        """
        Apply this blame filter to a list of results, return the results that pass the filter
        and as a side-effect, update the filter stats.
        """
        self._zero_counts()
        if self.apply_inclusion_filter or self.apply_exclusion_filter:
            ret = []
            for result in results:
                blame_info = result.get("properties", {}).get("blame", None)
                self._filter_append(ret, result, blame_info)
            return ret
        # No inclusion or exclusion patterns
        return results

    def get_filter_stats(self) -> Optional[FilterStats]:
        """
        Get the statistics from running this filter.
        """
        return self.filter_stats


class SarifRun:
    """
    Class to hold a run object from a SARIF file (an entry in the top-level "runs" list
    in a SARIF file), as defined in SARIF standard section 3.14.
    https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317484
    """

    def __init__(self, sarif_file_object, run_index, run_data):
        self.sarif_file = sarif_file_object
        self.run_index = run_index
        self.run_data = run_data
        self._path_prefixes_upper = None
        self._cached_records = None
        self._filter = _BlameFilter()
        self._default_line_number = None

    def init_path_prefix_stripping(self, autotrim=False, path_prefixes=None):
        """
        Set up path prefix stripping.  When records are subsequently obtained, the start of the
        path is stripped.
        If no path_prefixes are specified, the default behaviour is to strip the common prefix
        from each run.
        If path prefixes are specified, the specified prefixes are stripped.
        """
        prefixes = []
        if path_prefixes:
            prefixes = [prefix.strip().upper() for prefix in path_prefixes]
        if autotrim:
            autotrim_prefix = None
            records = self.get_records()
            if len(records) == 1:
                loc = records[0]["Location"].strip()
                slash_pos = max(loc.rfind(slash) for slash in _SLASHES)
                autotrim_prefix = loc[0:slash_pos] if slash_pos > -1 else None
            elif len(records) > 1:
                common_prefix = records[0]["Location"].strip()
                for record in records[1:]:
                    for (char_pos, char) in enumerate(record["Location"].strip()):
                        if char_pos >= len(common_prefix):
                            break
                        if char != common_prefix[char_pos]:
                            common_prefix = common_prefix[0:char_pos]
                            break
                    if not common_prefix:
                        break
                if common_prefix:
                    autotrim_prefix = common_prefix.upper()
            if autotrim_prefix and not any(
                p.startswith(autotrim_prefix.strip().upper()) for p in prefixes
            ):
                prefixes.append(autotrim_prefix)
        self._path_prefixes_upper = prefixes or None
        # Clear the untrimmed records cached by get_records() above.
        self._cached_records = None

    def init_default_line_number_1(self):
        """
        Some SARIF records lack a line number.  If this method is called, the default line number
        "1" is substituted in that case in the records returned by get_records().  Otherwise,
        None is returned.
        """
        self._default_line_number = "1"
        self._cached_records = None

    def init_blame_filter(
        self,
        filter_description,
        include_substrings,
        include_regexes,
        exclude_substrings,
        exclude_regexes,
    ):
        """
        Set up blame filtering.  This is applied to the author_mail field added to the "blame"
        property bag in each SARIF file.  Raises an error if any of the SARIF files don't contain
        blame information.
        If only inclusion criteria are provided, only issues matching the inclusion criteria
        are considered.
        If only exclusion criteria are provided, only issues not matching the exclusion criteria
        are considered.
        If both are provided, only issues matching the inclusion criteria and not matching the
        exclusion criteria are considered.
        include_substrings = substrings of author_mail to filter issues for inclusion.
        include_regexes = regular expressions for author_mail to filter issues for inclusion.
        exclude_substrings = substrings of author_mail to filter issues for exclusion.
        exclude_regexes = regular expressions for author_mail to filter issues for exclusion.
        """
        self._filter.init_blame_filter(
            filter_description,
            include_substrings,
            include_regexes,
            exclude_substrings,
            exclude_regexes,
        )
        # Clear the unfiltered records cached by get_records() above.
        self._cached_records = None

    def get_tool_name(self) -> str:
        """
        Get the tool name from this run.
        """
        return self.run_data["tool"]["driver"]["name"]

    def get_results(self) -> List[Dict]:
        """
        Get the results from this run.  These are the Result objects as defined in the SARIF
        standard section 3.27.  The results are filtered if a filter has ben configured.
        https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317638
        """
        return self._filter.filter_results(self.run_data["results"])

    def get_records(self) -> List[Dict]:
        """
        Get simplified records derived from the results of this run.  The records have the
        keys defined in `RECORD_ATTRIBUTES`.
        """
        if not self._cached_records:
            results = self.get_results()
            self._cached_records = [self.result_to_record(result) for result in results]
        return self._cached_records

    def get_records_grouped_by_severity(self) -> Dict[str, List[Dict]]:
        """
        Get the records, grouped by severity.
        """
        return _group_records_by_severity(self.get_records())

    def result_to_record(self, result):
        """
        Convert a SARIF result object to a simple record with fields "Tool", "Location", "Line",
        "Severity" and "Code".
        See definition of result object here:
        https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317638
        """
        error_id = result["ruleId"]
        tool_name = self.get_tool_name()
        (file_path, line_number) = _read_result_location(result)
        if not file_path:
            raise ValueError(f"No location in {error_id} output from {tool_name}")
        if not line_number:
            line_number = "1"

        if self._path_prefixes_upper:
            file_path_upper = file_path.upper()
            for prefix in self._path_prefixes_upper:
                if file_path_upper.startswith(prefix):
                    prefixlen = len(prefix)
                    if len(file_path) > prefixlen and file_path[prefixlen] in _SLASHES:
                        # Strip off trailing path separator
                        file_path = file_path[prefixlen + 1 :]
                    else:
                        file_path = file_path[prefixlen:]
                    break

        # Get the error severity, if included, and code
        severity = result.get(
            "level", "warning"
        )  # If an error has no specified level then by default it is a warning
        message = result["message"]["text"]

        # Create a dict representing this result
        record = {
            "Tool": tool_name,
            "Location": file_path,
            "Line": line_number,
            "Severity": severity,
            "Code": f"{error_id} {message}",
        }
        return record

    def get_result_count(self) -> int:
        """
        Return the total number of results.
        """
        return len(self.get_results())

    def get_result_count_by_severity(self) -> Dict[str, int]:
        """
        Return a dict from SARIF severity to number of records.
        """
        records = self.get_records()
        return {
            severity: sum(1 for record in records if severity in record["Severity"])
            for severity in SARIF_SEVERITIES
        }

    def get_issue_code_histogram(self, severity) -> List[Tuple]:
        """
        Return a list of pairs (code, count) of the records with the specified
        severities.
        """
        return _count_records_by_issue_code(self.get_records(), severity)

    def get_filter_stats(self) -> Optional[FilterStats]:
        """
        Get the number of records that were included or excluded by the filter.
        """
        return self._filter.get_filter_stats()


class SarifFile:
    """
    Class to hold SARIF data parsed from a file and provide accesssors to the data.
    """

    def __init__(self, file_path, data):
        self.abs_file_path = os.path.abspath(file_path)
        self.data = data
        self.runs = [
            SarifRun(self, run_index, run_data)
            for (run_index, run_data) in enumerate(self.data.get("runs", []))
        ]

    def __bool__(self):
        """
        True if non-empty.
        """
        return bool(self.runs)

    def init_path_prefix_stripping(self, autotrim=False, path_prefixes=None):
        """
        Set up path prefix stripping.  When records are subsequently obtained, the start of the
        path is stripped.
        If no path_prefixes are specified, the default behaviour is to strip the common prefix
        from each run.
        If path prefixes are specified, the specified prefixes are stripped.
        """
        for run in self.runs:
            run.init_path_prefix_stripping(autotrim, path_prefixes)

    def init_default_line_number_1(self):
        """
        Some SARIF records lack a line number.  If this method is called, the default line number
        "1" is substituted in that case in the records returned by get_records().  Otherwise,
        None is returned.
        """
        for run in self.runs:
            run.init_default_line_number_1()

    def init_blame_filter(
        self,
        filter_description,
        include_substrings,
        include_regexes,
        exclude_substrings,
        exclude_regexes,
    ):
        """
        Set up blame filtering.  This is applied to the author_mail field added to the "blame"
        property bag in each SARIF file.  Raises an error if any of the SARIF files don't contain
        blame information.
        If only inclusion criteria are provided, only issues matching the inclusion criteria
        are considered.
        If only exclusion criteria are provided, only issues not matching the exclusion criteria
        are considered.
        If both are provided, only issues matching the inclusion criteria and not matching the
        exclusion criteria are considered.
        include_substrings = substrings of author_mail to filter issues for inclusion.
        include_regexes = regular expressions for author_mail to filter issues for inclusion.
        exclude_substrings = substrings of author_mail to filter issues for exclusion.
        exclude_regexes = regular expressions for author_mail to filter issues for exclusion.
        """
        for run in self.runs:
            run.init_blame_filter(
                filter_description,
                include_substrings,
                include_regexes,
                exclude_substrings,
                exclude_regexes,
            )

    def get_abs_file_path(self) -> str:
        """
        Get the absolute file path from which this SARIF data was loaded.
        """
        return self.abs_file_path

    def get_file_name(self) -> str:
        """
        Get the file name from which this SARIF data was loaded.
        """
        return os.path.basename(self.abs_file_path)

    def get_file_name_without_extension(self) -> str:
        """
        Get the file name from which this SARIF data was loaded, without extension.
        """
        file_name = self.get_file_name()
        return file_name[0 : file_name.index(".")] if "." in file_name else file_name

    def get_file_name_extension(self) -> str:
        """
        Get the extension of the file name from which this SARIF data was loaded.
        Initial "." exlcuded.
        """
        file_name = self.get_file_name()
        return file_name[file_name.index(".") + 1 :] if "." in file_name else ""

    def get_filename_timestamp(self) -> str:
        """
        Extract the timestamp from the filename and return the date-time string extracted.
        """
        parsed_date = re.findall(DATETIME_REGEX, self.get_file_name())
        return parsed_date if len(parsed_date) == 1 else None

    def get_distinct_tool_names(self):
        """
        Return a list of tool names that feature in the runs in this file.
        The list is deduplicated and sorted into alphabetical order.
        """
        return sorted(list(set(run.get_tool_name() for run in self.runs)))

    def get_results(self) -> List[Dict]:
        """
        Get the results from all runs in this file.  These are the Result objects as defined in the
        SARIF standard section 3.27.
        https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317638
        """
        ret = []
        for run in self.runs:
            ret += run.get_results()
        return ret

    def get_records(self) -> List[Dict]:
        """
        Get simplified records derived from the results of all runs.  The records have the
        keys defined in `RECORD_ATTRIBUTES`.
        """
        ret = []
        for run in self.runs:
            ret += run.get_records()
        return ret

    def get_records_grouped_by_severity(self) -> Dict[str, List[Dict]]:
        """
        Get the records, grouped by severity.
        """
        return _group_records_by_severity(self.get_records())

    def get_result_count(self) -> int:
        """
        Return the total number of results.
        """
        return sum(run.get_result_count() for run in self.runs)

    def get_result_count_by_severity(self) -> Dict[str, int]:
        """
        Return a dict from SARIF severity to number of records.
        """
        get_result_count_by_severity_per_run = [
            run.get_result_count_by_severity() for run in self.runs
        ]
        return {
            severity: sum(
                rc.get(severity, 0) for rc in get_result_count_by_severity_per_run
            )
            for severity in SARIF_SEVERITIES
        }

    def get_issue_code_histogram(self, severity) -> List[Tuple]:
        """
        Return a list of pairs (code, count) of the records with the specified
        severities.
        """
        return _count_records_by_issue_code(self.get_records(), severity)

    def get_filter_stats(self) -> Optional[FilterStats]:
        """
        Get the number of records that were included or excluded by the filter.
        """
        ret = None
        for run in self.runs:
            ret = _add_filter_stats(ret, run.get_filter_stats())
        return ret


class SarifFileSet:
    """
    Class representing a set of SARIF files.
    The "composite" pattern is used to allow multiple subdirectories.
    """

    def __init__(self):
        self.subdirs = []
        self.files = []

    def __bool__(self):
        """
        Return true if there are any SARIF files, regardless of whether they contain any runs.
        """
        return any(bool(subdir) for subdir in self.subdirs) or bool(self.files)

    def __len__(self):
        """
        Return the number of SARIF files, in total.
        """
        return sum(len(subdir) for subdir in self.subdirs) + sum(
            1 for f in self.files if f
        )

    def __iter__(self) -> Iterator[SarifFile]:
        """
        Iterate the SARIF files in this set.
        """
        for subdir in self.subdirs:
            for input_file in subdir.files:
                yield input_file
        for input_file in self.files:
            yield input_file

    def __getitem__(self, index) -> SarifFile:
        i = 0
        for subdir in self.subdirs:
            for input_file in subdir.files:
                if i == index:
                    return input_file
                i += 1
        return self.files[index - i]

    def get_description(self):
        """
        Get a description of the SARIF file set - the name of the single file or the number of
        files.
        """
        count = len(self)
        if count == 1:
            return self[0].get_file_name()
        return f"{count} files"

    def init_path_prefix_stripping(self, autotrim=False, path_prefixes=None):
        """
        Set up path prefix stripping.  When records are subsequently obtained, the start of the
        path is stripped.
        If no path_prefixes are specified, the default behaviour is to strip the common prefix
        from each run.
        If path prefixes are specified, the specified prefixes are stripped.
        """
        for subdir in self.subdirs:
            subdir.init_path_prefix_stripping(autotrim, path_prefixes)
        for input_file in self.files:
            input_file.init_path_prefix_stripping(autotrim, path_prefixes)

    def init_default_line_number_1(self):
        """
        Some SARIF records lack a line number.  If this method is called, the default line number
        "1" is substituted in that case in the records returned by get_records().  Otherwise,
        None is returned.
        """
        for subdir in self.subdirs:
            subdir.init_default_line_number_1()
        for input_file in self.files:
            input_file.init_default_line_number_1()

    def init_blame_filter(
        self,
        filter_description,
        include_substrings,
        include_regexes,
        exclude_substrings,
        exclude_regexes,
    ):
        """
        Set up blame filtering.  This is applied to the author_mail field added to the "blame"
        property bag in each SARIF file.  Raises an error if any of the SARIF files don't contain
        blame information.
        If only inclusion criteria are provided, only issues matching the inclusion criteria
        are considered.
        If only exclusion criteria are provided, only issues not matching the exclusion criteria
        are considered.
        If both are provided, only issues matching the inclusion criteria and not matching the
        exclusion criteria are considered.
        include_substrings = substrings of author_mail to filter issues for inclusion.
        include_regexes = regular expressions for author_mail to filter issues for inclusion.
        exclude_substrings = substrings of author_mail to filter issues for exclusion.
        exclude_regexes = regular expressions for author_mail to filter issues for exclusion.
        """
        for subdir in self.subdirs:
            subdir.init_blame_filter(
                filter_description,
                include_substrings,
                include_regexes,
                exclude_substrings,
                exclude_regexes,
            )
        for input_file in self.files:
            input_file.init_blame_filter(
                filter_description,
                include_substrings,
                include_regexes,
                exclude_substrings,
                exclude_regexes,
            )

    def add_dir(self, sarif_file_set):
        """
        Add a SarifFileSet as a subdirectory.
        """
        self.subdirs.append(sarif_file_set)

    def add_file(self, sarif_file_object: SarifFile):
        """
        Add a single SARIF file to the set.
        """
        self.files.append(sarif_file_object)

    def get_distinct_tool_names(self) -> List[str]:
        """
        Return a list of tool names that feature in the runs in these files.
        The list is deduplicated and sorted into alphabetical order.
        """
        all_tool_names = set()
        for subdir in self.subdirs:
            all_tool_names.update(subdir.get_distinct_tool_names())
        for input_file in self.files:
            all_tool_names.update(input_file.get_distinct_tool_names())

        return sorted(list(all_tool_names))

    def get_results(self) -> List[Dict]:
        """
        Get the results from all runs in all files.  These are the Result objects as defined in the
        SARIF standard section 3.27.
        https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html#_Toc34317638
        """
        ret = []
        for subdir in self.subdirs:
            ret += subdir.get_results()
        for input_file in self.files:
            ret += input_file.get_results()
        return ret

    def get_records(self) -> List[Dict]:
        """
        Get simplified records derived from the results of all runs.  The records have the
        keys defined in `RECORD_ATTRIBUTES`.
        """
        ret = []
        for subdir in self.subdirs:
            ret += subdir.get_records()
        for input_file in self.files:
            ret += input_file.get_records()
        return ret

    def get_records_grouped_by_severity(self) -> Dict[str, List[Dict]]:
        """
        Get the records, grouped by severity.
        """
        return _group_records_by_severity(self.get_records())

    def get_result_count(self) -> int:
        """
        Return the total number of results.
        """
        return sum(subdir.get_result_count() for subdir in self.subdirs) + sum(
            input_file.get_result_count() for input_file in self.files
        )

    def get_result_count_by_severity(self) -> Dict[str, int]:
        """
        Return a dict from SARIF severity to number of records.
        """
        result_counts_by_severity = []
        for subdir in self.subdirs:
            result_counts_by_severity.append(subdir.get_result_count_by_severity())
        for input_file in self.files:
            result_counts_by_severity.append(input_file.get_result_count_by_severity())
        return {
            severity: sum(rc.get(severity, 0) for rc in result_counts_by_severity)
            for severity in SARIF_SEVERITIES
        }

    def get_issue_code_histogram(self, severity) -> List[Tuple]:
        """
        Return a list of pairs (code, count) of the records with the specified
        severities.
        """
        return _count_records_by_issue_code(self.get_records(), severity)

    def get_filter_stats(self) -> Optional[FilterStats]:
        """
        Get the number of records that were included or excluded by the filter.
        """
        ret = None
        for subdir in self.subdirs:
            ret = _add_filter_stats(ret, subdir.get_filter_stats())
        for input_file in self.files:
            ret = _add_filter_stats(ret, input_file.get_filter_stats())
        return ret
