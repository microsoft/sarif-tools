import datetime
import json
import os
import tempfile

from sarif.operations import diff_op
from sarif import sarif_file

SARIF = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Access to field 'type' results in a dereference of a null pointer (loaded from variable 'json')"
                    },
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
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Dereference of null pointer (loaded from variable 's')"
                    },
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
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Access to field 'other' results in a dereference of a null pointer (loaded from variable 'json')"
                    },
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
            ],
        }
    ],
}

SARIF_WITH_ISSUES_REORDERED = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Access to field 'type' results in a dereference of a null pointer (loaded from variable 'json')"
                    },
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
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Access to field 'other' results in a dereference of a null pointer (loaded from variable 'json')"
                    },
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
                    "ruleId": "core.NullDereference",
                    "ruleIndex": 2,
                    "message": {
                        "text": "Dereference of null pointer (loaded from variable 's')"
                    },
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
            ],
        }
    ],
}


def test_diff_issues_reordered():
    mtime = datetime.datetime.now()
    sarif = sarif_file.SarifFile("SARIF", SARIF, mtime=mtime)
    sarif_reordered = sarif_file.SarifFile(
        "SARIF_WITH_ISSUES_REORDERED", SARIF_WITH_ISSUES_REORDERED, mtime=mtime
    )
    verify_no_diffs(sarif, sarif_reordered)
    verify_no_diffs(sarif_reordered, sarif)


def verify_no_diffs(old_sarif: sarif_file.SarifFile, new_sarif: sarif_file.SarifFile):
    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "diff.json")
        result = diff_op.print_diff(
            old_sarif, new_sarif, file_path, check_level="warning"
        )
        with open(file_path, "rb") as f_in:
            diff_dict = json.load(f_in)
        assert result == 0
        assert diff_dict == {
            "all": {"+": 0, "-": 0},
            "error": {"+": 0, "-": 0, "codes": {}},
            "warning": {"+": 0, "-": 0, "codes": {}},
            "note": {"+": 0, "-": 0, "codes": {}},
        }
