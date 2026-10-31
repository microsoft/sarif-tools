import datetime
import json
import os
import tempfile

from sarif.operations import codeclimate_op
from sarif import sarif_file

INPUT_SARIF = {
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


EXPECTED_OUTPUT_JSON = [
    {
        "type": "issue",
        "check_name": "CA2101",
        "description": "CA2101",
        "categories": ["Bug Risk"],
        "location": {
            "path": "file:///C:/Code/main.c",
            "lines": {"begin": 24},
        },
        "severity": "major",
        # Fingerprint scheme changed once for issue #104 (identity no longer includes
        # the absolute line, and adds a per-identity occurrence index). This literal
        # is the one-time migrated value; existing consumers see one fingerprint change.
        "fingerprint": "66eff5d58a2b88a25c2d92900903ff18",
    }
]


def test_code_climate():
    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("INPUT_SARIF", INPUT_SARIF, mtime=mtime)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "codeclimate.json")
        codeclimate_op.generate(
            input_sarif_file_set, file_path, output_multiple_files=False
        )

        with open(file_path, "rb") as f_in:
            output_json = json.load(f_in)

        assert output_json == EXPECTED_OUTPUT_JSON
