import json
import os
import tempfile

from sarif.operations import diff_op
from sarif import sarif_file

SARIF_WITH_1_ISSUE = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "CA2101",
                    "level": "error",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "file:///C:/Code/main.c",
                                    "index": 0,
                                },
                                "region": {"startLine": 24, "startColumn": 9},
                            }
                        }
                    ],
                }
            ],
        }
    ],
}

SARIF_WITH_2_ISSUES = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "CA2101",
                    "level": "error",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "file:///C:/Code/main.c",
                                    "index": 0,
                                },
                                "region": {"startLine": 24, "startColumn": 9},
                            }
                        }
                    ],
                },
                {
                    "ruleId": "CA2102",
                    "level": "error",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "file:///C:/Code/main.c",
                                    "index": 0,
                                },
                                "region": {"startLine": 34, "startColumn": 9},
                            }
                        }
                    ],
                },
            ],
            "columnKind": "utf16CodeUnits",
        }
    ],
}


def test_print_diff():
    old_sarif = sarif_file.SarifFile("SARIF_WITH_1_ISSUE", SARIF_WITH_1_ISSUE)
    new_sarif = sarif_file.SarifFile("SARIF_WITH_2_ISSUES", SARIF_WITH_2_ISSUES)
    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "diff.json")
        result = diff_op.print_diff(
            old_sarif, new_sarif, file_path, check_level="warning"
        )
        with open(file_path, "rb") as f_in:
            diff_dict = json.load(f_in)
        assert result == 1
        assert diff_dict == {
            "all": {"+": 1, "-": 0},
            "error": {
                "+": 1,
                "-": 0,
                "codes": {
                    "CA2102": {
                        "<": 0,
                        ">": 1,
                        "+@": [{"Location": "file:///C:/Code/main.c", "Line": 34}],
                    }
                },
            },
            "warning": {"+": 0, "-": 0, "codes": {}},
            "note": {"+": 0, "-": 0, "codes": {}},
        }
        # If issues have decreased, return value should be 0.
        assert (
            diff_op.print_diff(new_sarif, old_sarif, file_path, check_level="warning")
            == 0
        )
