import re
from typing import Optional, Tuple

from sarif.filter.filter_stats import FilterStats, load_filter_stats_from_json_camel_case


class BlameFilter:
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

    def rehydrate_filter_stats(self, dehydrated_filter_stats, filter_datetime):
        """
        Restore filter stats from the SARIF file directly, where they were recorded when the filter
        was previously run.

        Note that if init_blame_filter is called, these rehydrated stats are discarded.
        """
        self.filter_stats = load_filter_stats_from_json_camel_case(
            dehydrated_filter_stats
        )
        self.filter_stats.filter_datetime = filter_datetime

    def _zero_counts(self):
        if self.filter_stats:
            self.filter_stats.reset_counters()

    def _check_include_result(self, author_mail):
        author_mail_upper = author_mail.upper().strip()
        matched_include_substrings = None
        matched_include_regexes = None
        if self.apply_inclusion_filter:
            if self.include_substrings:
                matched_include_substrings = [
                    s for s in self.include_substrings if s in author_mail_upper
                ]
            if self.include_regexes:
                matched_include_regexes = [
                    r
                    for r in self.include_regexes
                    if re.search(r, author_mail, re.IGNORECASE)
                ]
            if (not matched_include_substrings) and (not matched_include_regexes):
                return False
        if self.exclude_substrings and any(
            s in author_mail_upper for s in self.exclude_substrings
        ):
            return False
        if self.exclude_regexes and any(
            re.search(r, author_mail, re.IGNORECASE) for r in self.exclude_regexes
        ):
            return False
        return {
            "state": "included",
            "matchedSubstring": [s.lower() for s in matched_include_substrings]
            if matched_include_substrings
            else [],
            "matchedRegex": [r.lower() for r in matched_include_regexes]
            if matched_include_regexes
            else [],
        }

    def _filter_append(self, filtered_results, result, blame_info):
        # Remove any existing filter log on the result
        result.setdefault("properties", {}).pop("filtered", None)
        author_mail = get_author_mail_from_blame_info(blame_info)
        if author_mail:
            # First, check inclusion
            included = self._check_include_result(author_mail)
            if included:
                self.filter_stats.filtered_in_result_count += 1
                included["filter"] = self.filter_stats.filter_description
                result["properties"]["filtered"] = included
                filtered_results.append(result)
            else:
                (_file_path, line_number) = _read_result_location(result)
                if line_number == "1" or not line_number:
                    # Line number is not convincing.  Blame information may be misattributed.
                    self.filter_stats.unconvincing_line_number_count += 1
                    result["properties"]["filtered"] = {
                        "filter": self.filter_stats.filter_description,
                        "state": "default",
                        "missing": "line",
                    }
                    filtered_results.append(result)
                else:
                    self.filter_stats.filtered_out_result_count += 1
        else:
            self.filter_stats.missing_blame_count += 1
            # Result did not contain complete blame information, so don't filter it out.
            result["properties"]["filtered"] = {
                "filter": self.filter_stats.filter_description,
                "state": "default",
                "missing": "blame",
            }
            filtered_results.append(result)

    def filter_results(self, results):
        """
        Apply this blame filter to a list of results, return the results that pass the filter
        and as a side-effect, update the filter stats.
        """
        if self.apply_inclusion_filter or self.apply_exclusion_filter:
            self._zero_counts()
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


def get_author_mail_from_blame_info(blame_info):
    return (
        blame_info.get("author-mail", None) or blame_info.get("committer-mail", None)
        if blame_info
        else None
    )


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
