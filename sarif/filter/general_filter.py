import os
import re
from typing import Optional, List

import jsonpath_ng.ext
import yaml

from sarif.filter.filter_stats import FilterStats, \
    load_filter_stats_from_json

# Commonly used fields can be specified using shortcuts
# instead of full JSON path
FILTER_SHORTCUTS = {
    "author": "properties.blame.author",
    "author-mail": "properties.blame.author-mail",
    "committer": "properties.blame.committer",
    "committer-mail": "properties.blame.committer-mail",
    "location": "locations[*].physicalLocation.artifactLocation.uri",
    "rule": "ruleId",
    "suppression": "suppressions[*].kind"
}

# Some fields can have specific shortcuts to make it easier to write filters
# For example a file location can be specified using wildcards
FIELDS_REGEX_SHORTCUTS = {
    "uri": {
        "**": ".*",
        "*": "[^/]*",
        "?": "."
    }
}


def get_filter_function(filter_spec):
    if filter_spec:
        filter_len = len(filter_spec)
        if (
                filter_len > 2
                and filter_spec.startswith("/")
                and filter_spec.endswith("/")
        ):
            regex = filter_spec[1:-1]
            return lambda value: re.search(regex, value, re.IGNORECASE)
        else:
            substring = filter_spec
            # substring can be empty, in this case "in" returns true
            # and only existence of the property checked.
            return lambda value: substring in value
    return lambda value: True


def _convert_glob_to_regex(field_name, field_value_spec):
    # skip if field_value_spec is a regex
    if field_value_spec and \
            not (field_value_spec.startswith("/")
                 and field_value_spec.endswith("/")):
        # get last component of field name
        last_component = field_name.split(".")[-1]
        if last_component in FIELDS_REGEX_SHORTCUTS:
            shortcuts = FIELDS_REGEX_SHORTCUTS[last_component]
            rx = re.compile("|".join(map(re.escape, shortcuts.keys())))
            field_value_spec = rx.sub(
                lambda match: shortcuts[match.group(0)], field_value_spec
            )

            return f"/{field_value_spec}/"
    return field_value_spec


class GeneralFilter:
    """
    Class that implements filtering.
    """

    def __init__(self):
        self.filter_stats = None
        self.include_filters = {}
        self.apply_inclusion_filter = False
        self.exclude_filters = {}
        self.apply_exclusion_filter = False

    def init_filter(
        self,
        filter_description,
        include_filters,
        exclude_filters
    ):
        """
        Initialise the filter with the given filter patterns.
        """
        self.filter_stats = FilterStats(filter_description)
        self.include_filters = include_filters
        self.apply_inclusion_filter = len(include_filters) > 0
        self.exclude_filters = exclude_filters
        self.apply_exclusion_filter = len(exclude_filters) > 0

    def rehydrate_filter_stats(self, dehydrated_filter_stats, filter_datetime):
        """
        Restore filter stats from the SARIF file directly,
        where they were recorded when the filter was previously run.

        Note that if init_filter is called,
        these rehydrated stats are discarded.
        """
        self.filter_stats = load_filter_stats_from_json(
            dehydrated_filter_stats)
        self.filter_stats.filter_datetime = filter_datetime

    def _zero_counts(self):
        if self.filter_stats:
            self.filter_stats.reset_counters()

    def _filter_append(self, filtered_results: List[dict], result: dict):
        # Remove any existing filter log on the result
        result.setdefault("properties", {}).pop("filtered", None)

        matched_include_filters = []
        if self.apply_inclusion_filter:
            matched_include_filters = \
                self._filter_result(result, self.include_filters)
            if not matched_include_filters:
                return

        if self.apply_exclusion_filter:
            if self._filter_result(result, self.exclude_filters):
                self.filter_stats.filtered_out_result_count += 1
                return

        included = {
            "state": "included",
            "matchedFilter": matched_include_filters,
        }
        self.filter_stats.filtered_in_result_count += 1
        included["filter"] = self.filter_stats.filter_description
        result["properties"]["filtered"] = included

        filtered_results.append(result)

    def _filter_result(self, result: dict, filters: List[str]) -> List[dict]:
        matched_filters = []
        if filters:
            # filters contains rules which treated as OR.
            # if any rule matches, the record is selected.
            for filter_spec in filters:
                # filter_spec contains rules which treated as AND.
                # all rules must match to select the record.
                matched = True
                for (prop_path, prop_value_spec) in filter_spec.items():
                    resolved_prop_path = \
                        FILTER_SHORTCUTS.get(prop_path, prop_path)
                    jsonpath_expr = jsonpath_ng.ext.parse(resolved_prop_path)

                    found_results = jsonpath_expr.find(result)
                    if found_results:
                        value = found_results[0].value
                        value_spec = \
                            _convert_glob_to_regex(resolved_prop_path,
                                                    prop_value_spec)
                        filter_function = get_filter_function(value_spec)
                        if filter_function(value):
                            continue
                    matched = False
                    break
                if matched:
                    matched_filters.append(filter_spec)
        return matched_filters

    def filter_results(self, results: List[dict]) -> List[dict]:
        """
        Apply this filter to a list of results,
        return the results that pass the filter
        and as a side-effect, update the filter stats.
        """
        if self.apply_inclusion_filter or self.apply_exclusion_filter:
            self._zero_counts()
            ret = []
            for result in results:
                self._filter_append(ret, result)
            return ret
        # No inclusion or exclusion patterns
        return results

    def get_filter_stats(self) -> Optional[FilterStats]:
        """
        Get the statistics from running this filter.
        """
        return self.filter_stats


def load_filter_file(file_path):
    """
    Load a YAML filter file, return the filter description and the filters.
    """
    try:
        file_name = os.path.basename(file_path)
        with (open(file_path, encoding="utf-8") as file_in):
            yaml_content = yaml.safe_load(file_in)
            filter_description = yaml_content.get("description", file_name)
            include_filters = yaml_content.get("include", {})
            exclude_filters = yaml_content.get("exclude", {})
    except yaml.YAMLError as error:
        raise IOError(f"Cannot read filter file {file_path}") from error
    return (
        filter_description,
        include_filters,
        exclude_filters,
    )
