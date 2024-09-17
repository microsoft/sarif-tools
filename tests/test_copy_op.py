import datetime
import json
import jsonschema
import os
import tempfile

from sarif.operations import copy_op
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
                    "message": {"text": "just testing"},
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


def test_generate_sarif():
    # JSON Schema file for SARIF obtained from https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/
    sarif_schema_file = os.path.join(
        os.path.dirname(__file__), "sarif-schema-2.1.0.json"
    )
    with open(sarif_schema_file, "rb") as f_in:
        sarif_schema = json.load(f_in)
    input_sarif_file = sarif_file.SarifFile(
        "SARIF_WITH_1_ISSUE", SARIF_WITH_1_ISSUE, mtime=datetime.datetime.now()
    )
    jsonschema.validate(input_sarif_file.data, schema=sarif_schema)
    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)
    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "copied.json")
        output_sarif_file = copy_op.generate_sarif(
            input_sarif_file_set,
            file_path,
            append_timestamp=False,
            sarif_tools_version="1.2.3",
            cmdline="unit-test",
        )
        with open(file_path, "rb") as f_in:
            output_sarif = json.load(f_in)
        assert output_sarif_file.data == output_sarif
        jsonschema.validate(output_sarif, schema=sarif_schema)
