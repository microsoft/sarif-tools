"""
Regression tests for Code Climate issue identity (fingerprints) - issue #104.

A fingerprint must identify a diagnostic, not a place in a file, and duplicate
diagnostics with identical metadata must not be collapsed into one fingerprint.
"""

import datetime
import json
import os
import tempfile

import jsonschema

from sarif.operations import codeclimate_op
from sarif import sarif_file
from tests.utils import get_sarif_schema

INPUT_SARIF_SCHEMA = (
    "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json"
)

DEFAULT_PATH = "file:///C:/Code/main.c"


def _assert_schema_valid(doc):
    jsonschema.validate(instance=doc, schema=get_sarif_schema())


def _result(rule_id, message, line=24, path=DEFAULT_PATH, level="warning"):
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": path, "index": 0},
                    "region": {"startLine": line, "startColumn": 9},
                }
            }
        ],
    }


def _sarif_doc(results, tool_name="unit test"):
    return {
        "$schema": INPUT_SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {"tool": {"driver": {"name": tool_name}}, "results": results},
        ],
    }


def _sarif_file(name, results, tool_name="unit test"):
    return sarif_file.SarifFile(
        name,
        _sarif_doc(results, tool_name),
        mtime=datetime.datetime.now(),
    )


def _generate(tmp, files, output_multiple_files=False):
    file_set = sarif_file.SarifFileSet()
    for input_file in files:
        file_set.files.append(input_file)
    # With per-file output, "output" is the directory to write the several files into.
    output = tmp if output_multiple_files else os.path.join(tmp, "codeclimate.json")
    codeclimate_op.generate(file_set, output, output_multiple_files)
    return output


def _load(path):
    with open(path, "r", encoding="utf-8") as f_in:
        return json.load(f_in)


def _record(
    code="CA2101",
    description="Shared text",
    path=DEFAULT_PATH,
    line=24,
    tool="unit test",
    severity="warning",
):
    return {
        "Tool": tool,
        "Code": code,
        "Description": description,
        "Location": path,
        "Line": line,
        "Severity": severity,
    }


def _fingerprints_for_records(tmp, records, name="records.json"):
    output = os.path.join(tmp, name)
    codeclimate_op._write_to_json(records, output)
    return [issue["fingerprint"] for issue in _load(output)]


def test_line_shift_keeps_fingerprint_and_updates_location():
    """Unrelated code inserted above a diagnostic must not change its identity."""
    with tempfile.TemporaryDirectory() as tmp:
        before = _load(
            _generate(
                tmp,
                [
                    _sarif_file(
                        "before.sarif",
                        [_result("CA2101", "Avoid unsafe function", line=24)],
                    )
                ],
            )
        )

    with tempfile.TemporaryDirectory() as tmp:
        after = _load(
            _generate(
                tmp,
                [
                    _sarif_file(
                        "after.sarif",
                        [_result("CA2101", "Avoid unsafe function", line=108)],
                    )
                ],
            )
        )

    assert len(before) == 1
    assert len(after) == 1
    assert before[0]["fingerprint"] == after[0]["fingerprint"]
    # The reported location is still the real one, not a normalised placeholder.
    assert before[0]["location"]["lines"]["begin"] == 24
    assert after[0]["location"]["lines"]["begin"] == 108
    assert before[0]["location"]["path"] == DEFAULT_PATH


def test_repeated_generation_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        files = [
            _sarif_file(
                "input.sarif",
                [
                    _result("CA2101", "Avoid unsafe function", line=24),
                    _result("CA2102", "Use safe string", line=24),
                ],
            )
        ]
        first = _load(_generate(tmp, files))
        second = _load(_generate(tmp, files))

    assert len(first) == 2
    assert first == second


def test_unrelated_identity_insertion_and_reordering_keeps_fingerprints():
    alpha = _result("CA2101", "Avoid unsafe function", path="file:///C:/Code/a.c")
    beta = _result("CA2102", "Use safe string", path="file:///C:/Code/b.c")
    gamma = _result("CA2103", "Avoid unsafe call", path="file:///C:/Code/c.c", line=2)

    def fingerprints(files):
        with tempfile.TemporaryDirectory() as tmp:
            issues = _load(_generate(tmp, files))
        return {
            (issue["check_name"], issue["location"]["path"]): issue["fingerprint"]
            for issue in issues
        }

    baseline = fingerprints([_sarif_file("f.sarif", [alpha, beta])])
    reordered = fingerprints([_sarif_file("f.sarif", [beta, alpha])])
    inserted = fingerprints([_sarif_file("f.sarif", [alpha, gamma, beta])])

    assert (
        baseline[("CA2101", "file:///C:/Code/a.c")]
        == reordered[("CA2101", "file:///C:/Code/a.c")]
    )
    assert (
        baseline[("CA2102", "file:///C:/Code/b.c")]
        == reordered[("CA2102", "file:///C:/Code/b.c")]
    )
    assert (
        baseline[("CA2101", "file:///C:/Code/a.c")]
        == inserted[("CA2101", "file:///C:/Code/a.c")]
    )
    assert (
        baseline[("CA2102", "file:///C:/Code/b.c")]
        == inserted[("CA2102", "file:///C:/Code/b.c")]
    )
    assert ("CA2103", "file:///C:/Code/c.c") in inserted


def test_duplicate_identical_findings_get_unique_fingerprints():
    """Two/three indistinguishable diagnostics must all be reported, each distinct."""
    with tempfile.TemporaryDirectory() as tmp:
        issues = _load(
            _generate(
                tmp,
                [
                    _sarif_file(
                        "dupes.sarif",
                        [_result("CA2101", "Same text", line=24)] * 3,
                    )
                ],
            )
        )

    assert len(issues) == 3
    fingerprints = [issue["fingerprint"] for issue in issues]
    assert len(set(fingerprints)) == 3
    for issue in issues:
        assert issue["check_name"] == "CA2101"
        assert issue["location"] == {"path": DEFAULT_PATH, "lines": {"begin": 24}}
    # Each occurrence still gets its own 32-character fingerprint.
    assert len(issues[0]["fingerprint"]) == 32


def test_same_identity_at_different_lines_is_separated_by_occurrence():
    """Both duplicates keep their fingerprint when their lines shift and an unrelated
    diagnostic is inserted between them."""
    before_results = [
        _result("CA2101", "Same text", line=24),
        _result("CA2101", "Same text", line=57),
    ]
    after_results = [
        _result("CA2101", "Same text", line=124),
        _result("CA2102", "Unrelated inserted text", line=140),
        _result("CA2101", "Same text", line=157),
    ]
    after_doc = _sarif_doc(after_results)
    _assert_schema_valid(after_doc)

    with tempfile.TemporaryDirectory() as tmp:
        before = _load(_generate(tmp, [_sarif_file("before.sarif", before_results)]))
    with tempfile.TemporaryDirectory() as tmp:
        after = _load(
            _generate(
                tmp,
                [
                    sarif_file.SarifFile(
                        "after.sarif", after_doc, mtime=datetime.datetime.now()
                    )
                ],
            )
        )

    def duplicates(issues):
        return [issue for issue in issues if issue["check_name"] == "CA2101"]

    duplicates_before = duplicates(before)
    duplicates_after = duplicates(after)
    assert [issue["location"]["lines"]["begin"] for issue in duplicates_before] == [
        24,
        57,
    ]
    assert [issue["location"]["lines"]["begin"] for issue in duplicates_after] == [
        124,
        157,
    ]
    fingerprints_before = [issue["fingerprint"] for issue in duplicates_before]
    assert len(set(fingerprints_before)) == 2
    # Occurrence 0 and 1 keep their identity, so the inserted distinct diagnostic
    # does not consume a duplicate occurrence index.
    assert [issue["fingerprint"] for issue in duplicates_after] == fingerprints_before
    inserted = [issue for issue in after if issue["check_name"] == "CA2102"]
    assert len(inserted) == 1
    assert inserted[0]["fingerprint"] not in fingerprints_before


def test_different_tool_and_rule_do_not_collide():
    with tempfile.TemporaryDirectory() as tmp:
        doc = {
            "$schema": INPUT_SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "tool-a"}},
                    "results": [_result("CA2101", "Shared text")],
                },
                {
                    "tool": {"driver": {"name": "tool-b"}},
                    "results": [_result("CA2101", "Shared text")],
                },
                {
                    "tool": {"driver": {"name": "tool-a"}},
                    "results": [_result("CA2102", "Shared text")],
                },
            ],
        }
        input_file = sarif_file.SarifFile(
            "tools.sarif", doc, mtime=datetime.datetime.now()
        )
        issues = _load(_generate(tmp, [input_file]))

    assert len(issues) == 3
    assert [issue["check_name"] for issue in issues] == ["CA2101", "CA2101", "CA2102"]
    # Same description, path and line, different tool or rule: three identities.
    assert len(set(issue["fingerprint"] for issue in issues)) == 3


def test_canonical_serialization_avoids_ambiguity():
    """Separator-like and unicode text must not alias across field boundaries."""
    with tempfile.TemporaryDirectory() as tmp:
        fingerprints = _fingerprints_for_records(
            tmp,
            [
                _record(description="a b", path="c"),
                _record(description="a", path="b c"),
                _record(description="a\tb", path="c"),
                _record(description="a", path="b\tc"),
                _record(description='x","y', path="z", line=1),
                _record(description="x", path='","y","z', line=1),
                _record(description="\u6587\u4ef6 $ 1`]", path="\u8def\u5f84"),
                _record(description="\u6587\u4ef6", path=" $ 1`] \u8def\u5f84"),
                _record(description='{"identity": ["a"], "occurrence": 0}', path="p"),
                _record(description="a", path='"], "occurrence": 0}', line=1),
            ],
        )

    assert len(fingerprints) == 10
    assert len(set(fingerprints)) == 10


def test_other_codeclimate_fields_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        issues = _load(
            _generate(
                tmp,
                [
                    _sarif_file(
                        "fields.sarif",
                        [
                            _result(
                                "CA2101",
                                "Avoid unsafe function",
                                line=24,
                                level="error",
                            ),
                            _result("CA2102", "Use safe string", line=57, level="note"),
                        ],
                    )
                ],
            )
        )

    assert issues[0] == {
        "type": "issue",
        "check_name": "CA2101",
        "description": "Avoid unsafe function",
        "categories": ["Bug Risk"],
        "location": {"path": DEFAULT_PATH, "lines": {"begin": 24}},
        "severity": "major",
        "fingerprint": issues[0]["fingerprint"],
    }
    assert issues[1] == {
        "type": "issue",
        "check_name": "CA2102",
        "description": "Use safe string",
        "categories": ["Bug Risk"],
        "location": {"path": DEFAULT_PATH, "lines": {"begin": 57}},
        "severity": "info",
        "fingerprint": issues[1]["fingerprint"],
    }


def test_output_multiple_files_resets_occurrence_per_file():
    duplicate = [_result("CA2101", "Same text", line=24)]
    with tempfile.TemporaryDirectory() as tmp:
        first = _sarif_file("first.sarif", duplicate)
        second = _sarif_file("second.sarif", duplicate)
        _generate(tmp, [first, second], output_multiple_files=True)

        first_issues = _load(os.path.join(tmp, "first.json"))
        second_issues = _load(os.path.join(tmp, "second.json"))
        combined = _load(os.path.join(tmp, "static_analysis_output.json"))

    assert len(first_issues) == 1
    assert len(second_issues) == 1
    assert len(combined) == 2
    # Each emitted list numbers occurrences from zero: no counter leak between calls.
    assert first_issues[0]["fingerprint"] == second_issues[0]["fingerprint"]
    assert combined[0]["fingerprint"] == first_issues[0]["fingerprint"]
    assert combined[0]["fingerprint"] != combined[1]["fingerprint"]
