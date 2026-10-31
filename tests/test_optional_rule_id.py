"""Tests for SARIF results that legally omit ``ruleId``.

SARIF 2.1.0 permits a result without ``ruleId``: the result object schema requires
``message`` only.  Rule identity is therefore resolved through the existing
``sarif_file_utils.read_result_rule`` helper, with the tool driver name used as a
non-empty display fallback when no rule identity can be found.
"""

import copy
import datetime
import json
import os
import tempfile

import jsonschema
import pytest

from sarif import sarif_file
from sarif.operations import codeclimate_op

from tests.utils import get_sarif_schema

SCHEMA_URI = "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json"
TOOL_NAME = "typos"
FULL_MESSAGE = "`writter` should be `writer`, `written`"
URI = "file:///C:/Code/main.c"

RULES = [
    {"id": "R0", "name": "rule-zero"},
    {"id": "R1", "name": "rule-one"},
]

VALID_MISSING_ID_SARIF = {
    "version": "2.1.0",
    "$schema": SCHEMA_URI,
    "runs": [
        {
            "tool": {"driver": {"name": TOOL_NAME}},
            "results": [
                {
                    "level": "error",
                    "message": {
                        "markdown": FULL_MESSAGE,
                        "text": FULL_MESSAGE,
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "./packet/src/framing.rs"},
                                "region": {"startLine": 268, "startColumn": 23},
                            }
                        }
                    ],
                }
            ],
        }
    ],
}


def _result(message=None, **extra):
    result = {
        "level": "error",
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": URI, "index": 0},
                    "region": {"startLine": 24, "startColumn": 9},
                }
            }
        ],
    }
    result["message"] = {"text": FULL_MESSAGE} if message is None else message
    result.update(extra)
    return result


def _sarif_file(results, rules=None, tool_name=TOOL_NAME):
    driver = {"name": tool_name}
    if rules is not None:
        driver["rules"] = copy.deepcopy(rules)
    return sarif_file.SarifFile(
        "unit test",
        {
            "version": "2.1.0",
            "$schema": SCHEMA_URI,
            "runs": [{"tool": {"driver": driver}, "results": results}],
        },
        mtime=datetime.datetime.now(),
    )


def _record(results, rules=None, tool_name=TOOL_NAME):
    return _sarif_file(results, rules, tool_name).get_records()[0]


@pytest.mark.parametrize(
    "case,result_extra,rules,expected_code",
    [
        # No ruleId and no rule metadata at all: driver name is the fallback.
        ("absent-no-rules", {}, None, TOOL_NAME),
        ("absent-empty-rules", {}, [], TOOL_NAME),
        # ruleIndex is honoured, including index 0 (falsy but valid).
        ("rule-index-0", {"ruleIndex": 0}, RULES, "R0"),
        ("rule-index-1", {"ruleIndex": 1}, RULES, "R1"),
        # rule.index is the fallback location reference.
        ("rule-object-index", {"rule": {"index": 1}}, RULES, "R1"),
        # rule.id can be resolved against the descriptor array...
        ("rule-object-id", {"rule": {"id": "R1"}}, RULES, "R1"),
        # ...or preserved directly when no descriptor array is available.
        ("rule-object-id-no-rules", {"rule": {"id": "R9"}}, None, "R9"),
        # An explicit ruleId always wins over ruleIndex / rule.id.
        (
            "explicit-rule-id-priority",
            {"ruleId": "EXPLICIT", "ruleIndex": 0, "rule": {"id": "R1"}},
            RULES,
            "EXPLICIT",
        ),
        # Unresolvable index falls back safely instead of raising.
        ("unresolvable-index", {"ruleIndex": 9}, RULES, TOOL_NAME),
        ("negative-index", {"ruleIndex": -1}, RULES, TOOL_NAME),
    ],
)
def test_rule_identity_resolution(case, result_extra, rules, expected_code):
    record = _record([_result(**result_extra)], rules)
    assert record["Code"] == expected_code, case
    assert record["Description"] == FULL_MESSAGE, case


@pytest.mark.parametrize(
    "case,result_extra,rules,expected_code",
    [
        ("rule-index", {"ruleIndex": 0}, RULES, "R0"),
        ("rule-object-index", {"rule": {"index": 1}}, RULES, "R1"),
        ("rule-object-id", {"rule": {"id": "R1"}}, RULES, "R1"),
        ("rule-object-id-no-rules", {"rule": {"id": "R9"}}, None, "R9"),
    ],
)
def test_message_starting_with_resolved_id_is_retained(
    case, result_extra, rules, expected_code
):
    """Results without ``ruleId`` must never lose their message prefix.

    Only an explicit ``result.ruleId`` enables the legacy prefix stripping, so a
    newly supported result must keep its message even when that message begins
    with the descriptor or reference id resolved for it.
    """
    message = expected_code + ": full diagnostic detail for this result"
    record = _record([_result({"text": message}, **result_extra)], rules)
    assert record["Code"] == expected_code, case
    assert record["Description"] == message, case


def test_fallback_uses_tool_name_and_is_not_empty():
    record = _record([_result()], None)
    assert record["Tool"] == TOOL_NAME
    assert record["Code"] == TOOL_NAME
    assert record["Description"] == FULL_MESSAGE


def test_fallback_message_starting_with_tool_name_is_preserved():
    message = "typos: unexpected token while parsing the file"
    record = _record([_result({"text": message})], None)
    assert record["Code"] == TOOL_NAME
    assert record["Description"] == message


def test_missing_metadata_and_missing_message_text_uses_tool_name():
    record = _record([{"ruleIndex": 3, "level": "note"}], None)
    assert record["Code"] == TOOL_NAME
    assert record["Description"] == TOOL_NAME


@pytest.mark.parametrize(
    "message,expected",
    [
        ({"text": FULL_MESSAGE}, FULL_MESSAGE),
        ({"id": "SomeMessageId"}, "SomeMessageId"),
        ({"text": FULL_MESSAGE, "markdown": "**ignored**"}, FULL_MESSAGE),
    ],
)
def test_message_text_and_id_are_retained(message, expected):
    record = _record([_result(message)], None)
    assert record["Code"] == TOOL_NAME
    assert record["Description"] == expected


def test_malformed_markdown_only_message_still_raises_ioerror():
    # A message carrying only "markdown" violates the repository schema, which
    # requires text or id; this fix must not make that case lenient.
    with pytest.raises(IOError, match="RFC3629"):
        _record([_result({"markdown": FULL_MESSAGE})], None)


def test_default_severity_comes_from_resolved_descriptor():
    rules = [{"id": "R0", "defaultConfiguration": {"level": "error"}}]
    result = _result(ruleIndex=0)
    del result["level"]
    record = _record([result], rules)
    assert record["Code"] == "R0"
    assert record["Severity"] == "error"


def test_severity_defaults_to_warning_without_rule_metadata():
    result = _result()
    del result["level"]
    record = _record([result], None)
    assert record["Code"] == TOOL_NAME
    assert record["Severity"] == "warning"


def test_valid_missing_id_sarif_matches_schema_and_generates_record():
    jsonschema.validate(VALID_MISSING_ID_SARIF, schema=get_sarif_schema())

    record = sarif_file.SarifFile(
        "missing-id",
        copy.deepcopy(VALID_MISSING_ID_SARIF),
        mtime=datetime.datetime.now(),
    ).get_records()[0]
    assert record["Tool"] == TOOL_NAME
    assert record["Code"] == TOOL_NAME
    assert record["Description"] == FULL_MESSAGE
    assert record["Location"] == "./packet/src/framing.rs"
    assert record["Line"] == 268


def _mixed_sarif():
    return {
        "version": "2.1.0",
        "$schema": SCHEMA_URI,
        "runs": [
            {
                "tool": {"driver": {"name": TOOL_NAME, "rules": copy.deepcopy(RULES)}},
                "results": [
                    # The explicit-id message deliberately does not start with the
                    # id, so this assertion does not depend on the separate
                    # prefix-stripping behaviour tracked by #115.
                    _result(
                        message={"text": "Explicit id result text"}, ruleId="CA2101"
                    ),
                    _result(message={"text": FULL_MESSAGE}, ruleIndex=0, level="note"),
                    _result(
                        message={"text": "typos: no rule id supplied"},
                        locations=[
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": URI, "index": 1},
                                    "region": {"startLine": 99},
                                }
                            }
                        ],
                    ),
                ],
            }
        ],
    }


def test_codeclimate_mixed_results_are_all_retained():
    sarif = _mixed_sarif()
    jsonschema.validate(sarif, schema=get_sarif_schema())
    snapshot = copy.deepcopy(sarif)

    input_files = sarif_file.SarifFileSet()
    input_files.files.append(
        sarif_file.SarifFile("INPUT_SARIF", sarif, mtime=datetime.datetime.now())
    )
    # Reproduce the CLI chain: path prefix stripping applies to every record.
    input_files.init_path_prefix_stripping(False, ["file:///C:/Code/"])

    outputs = []
    with tempfile.TemporaryDirectory() as tmp:
        for run_index in range(2):
            out_path = os.path.join(tmp, f"codeclimate-{run_index}.json")
            codeclimate_op.generate(input_files, out_path, output_multiple_files=False)
            with open(out_path, "rb") as f_in:
                outputs.append(json.load(f_in))

    issues = outputs[0]
    assert len(issues) == 3
    assert [issue["check_name"] for issue in issues] == ["CA2101", "R0", TOOL_NAME]
    assert [issue["description"] for issue in issues] == [
        "Explicit id result text",
        FULL_MESSAGE,
        "typos: no rule id supplied",
    ]
    assert [issue["severity"] for issue in issues] == ["major", "info", "major"]
    assert [issue["location"] for issue in issues] == [
        {"path": "main.c", "lines": {"begin": 24}},
        {"path": "main.c", "lines": {"begin": 24}},
        {"path": "main.c", "lines": {"begin": 99}},
    ]

    fingerprints = [issue["fingerprint"] for issue in issues]
    assert len(set(fingerprints)) == 3
    for fingerprint in fingerprints:
        assert len(fingerprint) == 32
        int(fingerprint, 16)
    assert outputs[0] == outputs[1]
    assert sarif == snapshot
