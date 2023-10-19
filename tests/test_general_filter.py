import pytest
from sarif.filter.general_filter import GeneralFilter, load_filter_file
from sarif.filter.filter_stats import load_filter_stats_from_json


class TestGeneralFilter:
    def test_init_filter(self):
        gf = GeneralFilter()

        gf.init_filter(
            "test filter",
            {},
            [{"author": "John Doe"}],
            [{"suppression": "not a suppression"}],
        )
        assert gf.filter_stats.filter_description == "test filter"
        assert gf.include_filters == [{"author": "John Doe"}]
        assert gf.apply_inclusion_filter is True
        assert gf.exclude_filters == [{"suppression": "not a suppression"}]
        assert gf.apply_exclusion_filter is True

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
        general_filter.init_filter("test filter", {}, [{"ruleId": "test-rule"}], [])
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
        general_filter.init_filter("test filter", {}, [], [])
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert "filtered" not in result

    def test_filter_results_match(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter", {}, [{"ruleId": "test-rule"}, {"level": "error"}], []
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
            "test filter", {}, [{"ruleId": "other-rule"}, {"level": "warning"}], []
        )
        result = {"ruleId": "test-rule", "level": "error"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0

    def test_filter_results_regex(self):
        general_filter = GeneralFilter()
        rule = {"properties.blame.author-mail": "/myname\\..*\\.com/"}
        general_filter.init_filter(
            "test filter",
            {},
            [rule],
            [],
        )
        result = {
            "ruleId": "test-rule",
            "properties": {"blame": {"author-mail": "user@myname.example.com"}},
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
            {},
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
        general_filter.init_filter("test filter", {}, [], [{"suppression": {}}])
        result = {"ruleId": "test-rule", "suppressions": [{"kind": "inSource"}]}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0

    def test_filter_results_match_default_include_default_configuration(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [{"level": "error"}], [])
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "default"
        assert filtered_results[0]["properties"]["filtered"]["warnings"] == [
            "Field 'level' is missing but the result included as default-include is true"
        ]
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 1

    def test_filter_results_match_default_include_rule_override(self):
        general_filter = GeneralFilter()
        general_filter.init_filter(
            "test filter",
            {},
            [{"level": {"value": "error", "default-include": False}}],
            [],
        )
        result = {"ruleId": "test-rule"}

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 0
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
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
        general_filter.init_filter("test filter", {}, [shortcut_filter], [])

        filtered_results = general_filter.filter_results([result])
        assert len(filtered_results) == 1
        assert filtered_results[0] == result
        assert filtered_results[0]["properties"]["filtered"]["state"] == "included"
        assert "warnings" not in filtered_results[0]["properties"]["filtered"]

    def test_filter_results_include(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [{"ruleId": "test-rule"}], [])
        results = [{"ruleId": "test-rule"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 10
        assert all(result in filtered_results for result in results)
        assert general_filter.filter_stats.filtered_in_result_count == 10
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_results_exclude(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [], [{"level": "error"}])
        results = [{"level": "error"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 0
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 10
        assert general_filter.filter_stats.missing_property_count == 0

    def test_filter_results_exclude_not_all(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [], [{"level": "error"}])
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
        general_filter.init_filter("test filter", {}, [], [])
        results = [{"ruleId": "test-rule"}] * 10

        filtered_results = general_filter.filter_results(results)
        assert len(filtered_results) == 10
        assert all(result in filtered_results for result in results)
        assert general_filter.filter_stats.filtered_in_result_count == 0
        assert general_filter.filter_stats.filtered_out_result_count == 0
        assert general_filter.filter_stats.missing_property_count == 0

    def test_get_filter_stats(self):
        general_filter = GeneralFilter()
        general_filter.init_filter("test filter", {}, [{"ruleId": "test-rule"}], [])
        results = [{"ruleId": "test-rule"}] * 10

        general_filter.filter_results(results)
        filter_stats = general_filter.get_filter_stats()
        assert filter_stats.filtered_in_result_count == 10
        assert filter_stats.filtered_out_result_count == 0
        assert filter_stats.missing_property_count == 0

    def test_load_filter_file(self):
        file_path = "test_filter.yaml"
        filter_description = "Test filter"
        include_filters = {"ruleId": "test-rule"}
        exclude_filters = {"level": "error"}
        with open(file_path, "w") as f:
            f.write(f"description: {filter_description}\n")
            f.write(f"include:\n  ruleId: {include_filters['ruleId']}\n")
            f.write(f"exclude:\n  level: {exclude_filters['level']}\n")

        loaded_filter = load_filter_file(file_path)
        assert loaded_filter == (
            filter_description,
            {},
            include_filters,
            exclude_filters,
        )

    def test_load_filter_file_with_configuration(self):
        file_path = "test_filter.yaml"
        filter_description = "Test filter"
        configuration = {"default-include": True}
        include_filters = {"ruleId": "test-rule"}
        exclude_filters = {"level": "error"}
        with open(file_path, "w") as f:
            f.write(f"description: {filter_description}\n")
            f.write("configuration:\n  default-include: true\n")
            f.write(f"include:\n  ruleId: {include_filters['ruleId']}\n")
            f.write(f"exclude:\n  level: {exclude_filters['level']}\n")

        loaded_filter = load_filter_file(file_path)
        assert loaded_filter == (
            filter_description,
            configuration,
            include_filters,
            exclude_filters,
        )

    def test_load_filter_file_wrong_format(self):
        file_path = "test_filter.yaml"
        filter_description = "Test filter"
        with open(file_path, "w") as f:
            f.write(f"description: {filter_description}\n")
            f.write("include\n")
            f.write("exclude\n")

        with pytest.raises(IOError) as io_error:
            load_filter_file(file_path)
        assert str(io_error.value) == f"Cannot read filter file {file_path}"
