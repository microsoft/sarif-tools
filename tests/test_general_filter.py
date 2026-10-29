import datetime
from copy import deepcopy

import pytest
from sarif import sarif_file
from sarif.filter.general_filter import (
    FilterConfigurationError,
    GeneralFilter,
    load_filter_file,
)
from sarif.filter.filter_stats import FilterStats, load_filter_stats_from_json


def _result(result_id, **properties):
    result = {
        "id": result_id,
        "ruleId": "R1",
        "locations": [{"physicalLocation": {"region": {"startLine": "2"}}}],
    }
    result.update(properties)
    return result


def _general_filter(include=None, exclude=None, configuration=None):
    general_filter = GeneralFilter()
    general_filter.init_filter(
        "test filter",
        {"check-line-number": False, **(configuration or {})},
        include or [],
        exclude or [],
    )
    return general_filter


def _zero_match_warning(path, section, result_count):
    return (
        f"Filter path '{path}' in {section} matched no values in "
        f"{result_count} evaluated results. The path is valid JSONPath but may be "
        "misspelled or not applicable to this input. Filtering behavior was unchanged."
    )


class TestGeneralFilter:
    def test_documented_filter_structure_loads_and_compiles(self, tmp_path):
        filter_path = tmp_path / "filter.yaml"
        filter_path.write_text(
            "description: documented filter\n"
            "configuration:\n"
            "  default-include: false\n"
            "  check-line-number: true\n"
            "include:\n"
            "  - rule: R1\n"
            "    properties.custom.nested: value\n"
            "exclude:\n"
            "  - suppression:\n",
            encoding="utf-8",
        )

        loaded_filter = load_filter_file(filter_path)
        general_filter = GeneralFilter()
        general_filter.init_filter(*loaded_filter)

        assert len(general_filter.include_filters) == 1
        assert len(general_filter.include_filters[0].and_terms) == 2
        assert len(general_filter.exclude_filters) == 1

    @pytest.mark.parametrize("section", ["include", "exclude"])
    def test_malformed_filter_collection_has_contextual_error(self, tmp_path, section):
        filter_path = tmp_path / "filter.yaml"
        filter_path.write_text(f"{section}:\n  localtion: '*.py'\n", encoding="utf-8")
        loaded_filter = load_filter_file(filter_path)
        general_filter = GeneralFilter()

        with pytest.raises(ValueError, match=section):
            general_filter.init_filter(*loaded_filter)

    @pytest.mark.parametrize("section", ["include", "exclude"])
    def test_malformed_rule_has_contextual_error(self, section):
        general_filter = GeneralFilter()
        include = [["rule", "R1"]] if section == "include" else []
        exclude = [["rule", "R1"]] if section == "exclude" else []

        with pytest.raises(ValueError, match=rf"{section}\[0\]"):
            general_filter.init_filter("test filter", {}, include, exclude)

    def test_malformed_jsonpath_has_contextual_error(self):
        general_filter = GeneralFilter()

        with pytest.raises(
            ValueError, match=r"include\[0\].*locations\[.*invalid JSONPath"
        ):
            general_filter.init_filter("test filter", {}, [{"locations[": "value"}], [])

    def test_malformed_root_has_contextual_error(self, tmp_path):
        filter_path = tmp_path / "filter.yaml"
        filter_path.write_text("[]\n", encoding="utf-8")

        with pytest.raises(ValueError, match="root"):
            load_filter_file(filter_path)

    def test_malformed_configuration_has_contextual_error(self):
        general_filter = GeneralFilter()

        with pytest.raises(ValueError, match="configuration"):
            general_filter.init_filter("test filter", "invalid", [], [])

    def test_malformed_property_value_has_contextual_error(self):
        general_filter = GeneralFilter()

        with pytest.raises(ValueError, match=r"include\[0\].*ruleId"):
            general_filter.init_filter("test filter", {}, [{"ruleId": ["R1"]}], [])

    def test_undocumented_successful_empty_shapes_remain_accepted(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", [], {}, {})
        results = [_result("one")]

        assert general_filter.filter_results(results) is results

    @pytest.mark.parametrize("section", ["include", "exclude"])
    @pytest.mark.parametrize(
        "invalid_rule",
        [None, False, 0, "", [], {}],
        ids=["null", "false", "zero", "empty-string", "empty-list", "empty-mapping"],
    )
    def test_falsey_rule_entry_has_contextual_error(self, section, invalid_rule):
        general_filter = GeneralFilter()
        include = [invalid_rule] if section == "include" else []
        exclude = [invalid_rule] if section == "exclude" else []

        with pytest.raises(
            ValueError,
            match=rf"{section}\[0\] must be a non-empty mapping",
        ):
            general_filter.init_filter("test filter", {}, include, exclude)

    @pytest.mark.parametrize("section", ["include", "exclude"])
    def test_malformed_regex_has_contextual_error(self, section):
        general_filter = GeneralFilter()
        include = [{"ruleId": "/[/"}] if section == "include" else []
        exclude = [{"ruleId": "/[/"}] if section == "exclude" else []

        with pytest.raises(
            ValueError,
            match=rf"Invalid regular expression in {section}\[0\]\.ruleId",
        ):
            general_filter.init_filter("test filter", {}, include, exclude)

    def test_undocumented_zero_value_remains_existence_check(self):
        general_filter = _general_filter(include=[{"ruleId": 0}])

        filtered_results = general_filter.filter_results([_result("one")])

        assert [result["id"] for result in filtered_results] == ["one"]

    @pytest.mark.parametrize(
        ("path", "result"),
        [
            ("customTop", _result("top", customTop="value")),
            (
                "properties.custom.nested",
                _result("nested", properties={"custom": {"nested": "value"}}),
            ),
            (
                "commit",
                _result(
                    "commit",
                    commit="top-level",
                    properties={"blame": {"commit": "blame-value"}},
                ),
            ),
        ],
    )
    def test_arbitrary_jsonpath_remains_accepted(self, path, result):
        expected_value = "top-level" if path == "commit" else "value"
        general_filter = _general_filter(include=[{path: expected_value}])

        filtered_results = general_filter.filter_results([result])

        assert [item["id"] for item in filtered_results] == [result["id"]]
        assert general_filter.filter_stats.warnings == []

    @pytest.mark.parametrize(
        ("results", "expected_warnings"),
        [
            (
                [
                    _result("one", customTop="value"),
                    _result("two", customTop="value"),
                ],
                [],
            ),
            ([_result("one", customTop="value"), _result("two")], []),
            (
                [_result("one"), _result("two")],
                [_zero_match_warning("customTop", "include", 2)],
            ),
        ],
        ids=["present-everywhere", "present-somewhere", "absent-everywhere"],
    )
    def test_zero_match_warning_depends_on_collection_presence(
        self, results, expected_warnings
    ):
        general_filter = _general_filter(
            include=[{"customTop": "value"}],
            configuration={"default-include": False},
        )

        general_filter.filter_results(deepcopy(results))

        assert general_filter.filter_stats.warnings == expected_warnings

    def test_existing_path_with_unmatched_value_has_no_zero_match_warning(self):
        general_filter = _general_filter(
            include=[{"ruleId": "does-not-match"}],
            configuration={"default-include": False},
        )

        filtered_results = general_filter.filter_results([_result("one")])

        assert filtered_results == []
        assert general_filter.filter_stats.warnings == []

    def test_first_value_matching_remains_unchanged(self):
        general_filter = _general_filter(
            include=[{"items[*].value": "target"}],
            configuration={"default-include": False},
        )
        result = _result("one", items=[{"value": "other"}, {"value": "target"}])

        filtered_results = general_filter.filter_results([result])

        assert filtered_results == []
        assert general_filter.filter_stats.warnings == []

    def test_empty_results_have_no_zero_match_warning(self):
        general_filter = _general_filter(include=[{"missing": "value"}])

        assert general_filter.filter_results([]) == []
        assert general_filter.filter_stats.warnings == []

    @pytest.mark.parametrize(
        (
            "section",
            "default_include",
            "expected_ids",
            "expected_counts",
        ),
        [
            ("include", True, ["one", "two"], (0, 0, 2)),
            ("include", False, [], (0, 2, 0)),
            ("exclude", True, [], (0, 2, 0)),
            ("exclude", False, ["one", "two"], (2, 0, 0)),
        ],
    )
    def test_zero_match_diagnostic_preserves_default_include_behavior(
        self, section, default_include, expected_ids, expected_counts
    ):
        include = [{"missing": "value"}] if section == "include" else []
        exclude = [{"missing": "value"}] if section == "exclude" else []
        general_filter = _general_filter(
            include=include,
            exclude=exclude,
            configuration={"default-include": default_include},
        )
        results = [_result("one"), _result("two")]

        filtered_results = general_filter.filter_results(results)

        assert [result["id"] for result in filtered_results] == expected_ids
        assert (
            general_filter.filter_stats.filtered_in_result_count,
            general_filter.filter_stats.filtered_out_result_count,
            general_filter.filter_stats.missing_property_count,
        ) == expected_counts
        assert general_filter.filter_stats.warnings == [
            _zero_match_warning("missing", section, 2)
        ]

    def test_or_short_circuit_does_not_hide_observational_warning(self):
        general_filter = _general_filter(
            include=[{"ruleId": "R1"}, {"missing": "value"}]
        )
        skipped_matcher = general_filter.include_filters[1].and_terms[0]
        skipped_matcher.filter_function = lambda _value: pytest.fail(
            "value matcher must remain short-circuited"
        )

        filtered_results = general_filter.filter_results([_result("one")])

        assert [result["id"] for result in filtered_results] == ["one"]
        assert general_filter.filter_stats.warnings == [
            _zero_match_warning("missing", "include", 1)
        ]

    def test_and_short_circuit_does_not_hide_observational_warning(self):
        general_filter = _general_filter(
            include=[{"level": "note", "missing": "value"}],
            configuration={"default-include": False},
        )
        skipped_matcher = general_filter.include_filters[0].and_terms[1]
        skipped_matcher.filter_function = lambda _value: pytest.fail(
            "value matcher must remain short-circuited"
        )

        filtered_results = general_filter.filter_results(
            [_result("one", level="warning")]
        )

        assert filtered_results == []
        assert general_filter.filter_stats.warnings == [
            _zero_match_warning("missing", "include", 1)
        ]

    def test_check_line_number_skip_does_not_hide_existing_path(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [{"rule": "R1"}], [])
        result = _result("one")
        result["locations"][0]["physicalLocation"]["region"]["startLine"] = "1"

        filtered_results = general_filter.filter_results([result])

        assert [item["id"] for item in filtered_results] == ["one"]
        assert general_filter.filter_stats.unconvincing_line_number_count == 1
        assert general_filter.filter_stats.warnings == []

    def test_duplicate_paths_have_one_deterministic_warning(self):
        general_filter = _general_filter(
            include=[{"missing": "one"}, {"missing": "two"}]
        )

        general_filter.filter_results([_result("one")])

        assert general_filter.filter_stats.warnings == [
            _zero_match_warning("missing", "include", 1)
        ]

    @pytest.mark.parametrize(
        ("path", "expected_warning"),
        [
            (
                "items[?(@.kind == 'target')].value",
                True,
            ),
            ("items[5].value", True),
            ("items[0:1].value", False),
        ],
    )
    def test_complex_jsonpath_zero_match_is_neutral(self, path, expected_warning):
        general_filter = _general_filter(
            include=[{path: "value"}],
            configuration={"default-include": False},
        )

        general_filter.filter_results(
            [_result("one", items=[{"kind": "other", "value": "value"}])]
        )

        if expected_warning:
            assert general_filter.filter_stats.warnings == [
                _zero_match_warning(path, "include", 1)
            ]
        else:
            assert general_filter.filter_stats.warnings == []

    def test_filter_stats_aggregate_path_observations(self):
        absent_filter = _general_filter(include=[{"customTop": "value"}])
        absent_filter.filter_results([_result("absent")])
        present_filter = _general_filter(include=[{"customTop": "value"}])
        present_filter.filter_results([_result("present", customTop="value")])
        total = FilterStats("test filter")

        total.add(absent_filter.filter_stats)
        total.add(present_filter.filter_stats)

        assert total.warnings == []
        assert "warnings" not in total.to_json_camel_case()

        absent_total = FilterStats("test filter")
        absent_total.add(absent_filter.filter_stats)
        absent_total.add(absent_filter.filter_stats)
        assert absent_total.warnings == [_zero_match_warning("customTop", "include", 2)]
        assert f"Warning: {absent_total.warnings[0]}" in absent_total.to_string()

    def test_sarif_file_filter_stats_aggregation_is_observational(self):
        sarif_data = {
            "runs": [
                {
                    "tool": {"driver": {"name": "tool-a"}},
                    "results": [_result("one")],
                },
                {
                    "tool": {"driver": {"name": "tool-b"}},
                    "results": [_result("two")],
                },
            ]
        }
        input_file = sarif_file.SarifFile(
            "input.sarif",
            sarif_data,
            mtime=datetime.datetime.now(),
        )
        input_file.init_general_filter(
            "test filter",
            {"check-line-number": False},
            [{"missing": "value"}],
            [],
        )
        input_file.get_results()
        run_stats = [run.get_filter_stats() for run in input_file.runs]
        expected_run_warning = [_zero_match_warning("missing", "include", 1)]
        expected_aggregate_warning = [_zero_match_warning("missing", "include", 2)]

        assert [stats.warnings for stats in run_stats] == [
            expected_run_warning,
            expected_run_warning,
        ]

        aggregate_one = input_file.get_filter_stats()
        aggregate_one_warnings = list(aggregate_one.warnings)

        assert aggregate_one_warnings == expected_aggregate_warning
        assert [stats.warnings for stats in run_stats] == [
            expected_run_warning,
            expected_run_warning,
        ]

        aggregate_two = input_file.get_filter_stats()

        assert aggregate_two.warnings == expected_aggregate_warning
        assert aggregate_one.warnings == aggregate_one_warnings
        assert [stats.warnings for stats in run_stats] == [
            expected_run_warning,
            expected_run_warning,
        ]

    def test_path_observation_reads_original_result(self):
        general_filter = _general_filter(
            include=[{"properties.filtered.state": "legacy"}],
            configuration={"default-include": False},
        )
        result = _result("one", properties={"filtered": {"state": "legacy"}})

        filtered_results = general_filter.filter_results([result])

        assert filtered_results == []
        assert general_filter.filter_stats.warnings == []

    def test_empty_filter_remains_identity_operation(self):
        general_filter = _general_filter()
        results = [_result("one")]

        filtered_results = general_filter.filter_results(results)

        assert filtered_results is results
        assert general_filter.filter_stats.warnings == []

    def test_init_filter(self):
        gf = GeneralFilter()

        gf.init_filter(
            "test filter",
            {},
            [{"author": "John Doe"}],
            [{"suppression": "not a suppression"}],
        )
        assert gf.filter_stats.filter_description == "test filter"
        assert len(gf.include_filters[0].and_terms) == 1
        assert gf.include_filters[0].and_terms[0].prop_path == "author"
        assert gf.apply_inclusion_filter is True
        assert len(gf.exclude_filters[0].and_terms) == 1
        assert gf.exclude_filters[0].and_terms[0].prop_path == "suppression"
        assert gf.apply_exclusion_filter is True

    def test_init_filter_no_value(self):
        gf = GeneralFilter()

        gf.init_filter(
            "test filter",
            {},
            [{"author": {"default-include": False}}],  # forgot "value"
            [],
        )
        assert gf.filter_stats.filter_description == "test filter"
        assert len(gf.include_filters[0].and_terms) == 1
        assert gf.include_filters[0].and_terms[0].prop_path == "author"
        assert gf.apply_inclusion_filter is True
        assert not gf.exclude_filters

    def test_rehydrate_filter_stats(self):
        gf = GeneralFilter()
        dehydrated_filter_stats = {
            "filter": "test filter",
            "in": 10,
            "out": 5,
            "default": {"noProperty": 3},
        }
        gf.rehydrate_filter_stats(dehydrated_filter_stats, "2022-01-01T00:00:00Z")
        assert gf.filter_stats.filtered_in_result_count == 10
        assert gf.filter_stats.filtered_out_result_count == 5
        assert gf.filter_stats.missing_property_count == 3
        assert gf.filter_stats.filter_datetime == "2022-01-01T00:00:00Z"

    def test_zero_counts(self):
        gf = GeneralFilter()
        gf.filter_stats = load_filter_stats_from_json(
            {"filter": "test filter", "in": 10, "out": 5, "default": {"noProperty": 3}}
        )

        gf._zero_counts()
        assert gf.filter_stats.filtered_in_result_count == 0
        assert gf.filter_stats.filtered_out_result_count == 0
        assert gf.filter_stats.missing_property_count == 0

    def test_filter_append_include(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [{"ruleId": "test-rule"}], []
        )
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert general_filter.filter_stats.filtered_in_result_count == 1
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_append_exclude(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [], [{"level": "error"}])
        result = {"level": "error"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0
        assert "filtered" not in result
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 1
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_append_no_filters(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {"check-line-number": False}, [], [])
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert "filtered" not in result

    def test_filter_results_match(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter",
            {"check-line-number": False},
            [{"ruleId": "test-rule"}, {"level": "error"}],
            [],
        )
        result = {"ruleId": "test-rule", "level": "error"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert filtered_results[0]["properties"]["filtered"]["matchedFilter"] == [
            {"ruleId": "test-rule"}
        ]
        assert "warnings" not in filtered_results[0]["properties"]["filtered"]
        assert general_filter.filter_stats.filtered_in_result_count == 1
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_results_no_match(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter",
            {"check-line-number": False},
            [{"ruleId": "other-rule"}, {"level": "warning"}],
            [],
        )
        result = {"ruleId": "test-rule", "level": "error"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0

    def test_filter_results_regex(self):
        general_filter = GeneralFilter()
        rule = {"properties.blame.author-mail": "/myname\\..*\\.com/"}
        general_filter.init_filter(
            "test filter",
            {"check-line-number": True},
            [rule],
            [],
        )
        result = {
            "ruleId": "test-rule",
            "properties": {"blame": {"author-mail": "user@myname.example.com"}},
            "locations": [{"physicalLocation": {"region": {"startLine": "123"}}}],
        }

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert filtered_results[0]["properties"]["filtered"]["matchedFilter"] == [rule]
        assert "warnings" not in filtered_results[0]["properties"]["filtered"]

    def test_filter_results_regex_guid(self):
        general_filter = GeneralFilter()
        guid_rule = {
            "properties.blame.author-mail": "/[0-9A-F]{8}[-][0-9A-F]{4}[-][0-9A-F]{4}"
            + "[-][0-9A-F]{4}[-][0-9A-F]{12}/"
        }
        general_filter.init_filter(
            "test filter",
            {"check-line-number": False},
            [guid_rule],
            [],
        )
        result = {
            "ruleId": "test-rule",
            "properties": {
                "blame": {"author-mail": "AAAAA1234ABCD-FEDC-BA09-8765-4321ABCDEF90"}
            },
        }

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert filtered_results[0]["properties"]["filtered"]["matchedFilter"] == [
            guid_rule
        ]
        assert "warnings" not in filtered_results[0]["properties"]["filtered"]

    def test_filter_results_existence_only(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [], [{"suppression": {}}]
        )
        result = {"ruleId": "test-rule", "suppressions": [{"kind": "inSource"}]}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0

    def test_filter_results_match_default_include_default_configuration(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [{"level": "error"}], []
        )
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "noProperty"
        assert filtered_results[0]["properties"]["filtered"]["warnings"] == [
            "Field 'level' is missing but the result included as default-include is true"
        ]
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 1

    def test_filter_results_check_line_number(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [{"level": "error"}], [])
        result = {
            "ruleId": "test-rule",
            "locations": [{"physicalLocation": {"region": {"startLine": "1"}}}],
        }

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "noLineNumber"
        assert filtered_results[0]["properties"]["filtered"]["warnings"] == [
            "Field 'level' not checked due to missing line number information"
        ]
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0
        assert general_filter.filter_stats.unconvincing_line_number_count == 1

    def test_filter_results_match_default_include_rule_override(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter",
            {"check-line-number": False},
            [{"level": {"value": "error", "default-include": False}}],
            [],
        )
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0
        assert general_filter.filter_stats.filtered_in_result_count == 0
        # Filtered out because not filtered in
        assert general_filter.filter_stats.filtered_out_result_count == 1
        assert general_filter.filter_stats.missing_property_count == 0

    SHORTCUTS_TEST_PARAMS = [
        ({"author": "John Smith"}, {"properties": {"blame": {"author": "John Smith"}}}),
        (
            {"author-mail": "john.smith@example.com"},
            {"properties": {"blame": {"author-mail": "john.smith@example.com"}}},
        ),
        (
            {"committer-mail": "john.smith@example.com"},
            {"properties": {"blame": {"committer-mail": "john.smith@example.com"}}},
        ),
        (
            {"location": "test.cpp"},
            {
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": "test.cpp"}}}
                ]
            },
        ),
        ({"rule": "rule1"}, {"ruleId": "rule1"}),
        ({"suppression": "inSource"}, {"suppressions": [{"kind": "inSource"}]}),
    ]

    @pytest.mark.parametrize("shortcut_filter,result", SHORTCUTS_TEST_PARAMS)
    def test_filter_results_shortcuts(self, shortcut_filter, result):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [shortcut_filter], []
        )

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert "warnings" not in filtered_results[0]["properties"]["filtered"]

    def test_filter_results_include(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [{"ruleId": "test-rule"}], []
        )
        results = [{"ruleId": "test-rule"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 10
        assert all(result in filtered_results for result in results)
        assert general_filter.filter_stats.filtered_in_result_count == 10
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_results_exclude(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [], [{"level": "error"}]
        )
        results = [{"level": "error"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 0
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 10
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_results_exclude_not_all(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [], [{"level": "error"}]
        )
        results = [{"level": "error"}, {"level": "warning"}, {"level": "error"}]

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 1
        assert general_filter.filter_stats.filtered_in_result_count == 1
        assert general_filter.filter_stats.filtered_out_result_count == 2
        assert general_filter.filter_stats.missing_property_count == 0
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert len(filtered_results[0]["properties"]["filtered"]["matchedFilter"]) == 0

    def test_filter_results_no_filters(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {"check-line-number": False}, [], [])
        results = [{"ruleId": "test-rule"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 10
        assert all(result in filtered_results for result in results)
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_get_filter_stats(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {"check-line-number": False}, [{"ruleId": "test-rule"}], []
        )
        results = [{"ruleId": "test-rule"}] * 10

        general_filter.filter_results(results)
        filter_stats = general_filter.get_filter_stats()
        assert filter_stats.filtered_in_result_count == 10
        assert filter_stats.filtered_out_result_count == 0
        assert filter_stats.missing_property_count == 0

    def test_load_filter_file(self, tmp_path):
        file_path = tmp_path / "test_filter.yaml"
        filter_description = "Test filter"
        include_filters = [{"ruleId": "test-rule"}]
        exclude_filters = [{"level": "error"}]
        with open(file_path, "w") as f:
            f.write(f"description: {filter_description}\n")
            f.write("include:\n  - ruleId: test-rule\n")
            f.write("exclude:\n  - level: error\n")

        loaded_filter = load_filter_file(file_path)
        assert loaded_filter == (
            filter_description,
            {},
            include_filters,
            exclude_filters,
        )

    def test_load_filter_file_with_configuration(self, tmp_path):
        file_path = tmp_path / "test_filter.yaml"
        filter_description = "Test filter"
        configuration = {"default-include": True}
        include_filters = [{"ruleId": "test-rule"}]
        exclude_filters = [{"level": "error"}]
        with open(file_path, "w") as f:
            f.write(f"description: {filter_description}\n")
            f.write("configuration:\n  default-include: true\n")
            f.write("include:\n  - ruleId: test-rule\n")
            f.write("exclude:\n  - level: error\n")

        loaded_filter = load_filter_file(file_path)
        assert loaded_filter == (
            filter_description,
            configuration,
            include_filters,
            exclude_filters,
        )

    def test_load_filter_file_malformed_yaml_has_typed_error(self, tmp_path):
        file_path = tmp_path / "test_filter.yaml"
        file_path.write_text("include: [\n", encoding="utf-8")

        with pytest.raises(FilterConfigurationError) as config_error:
            load_filter_file(file_path)

        assert str(config_error.value) == (
            f"Invalid filter configuration in {file_path}: malformed YAML"
        )
