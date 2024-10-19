from copy import deepcopy
import datetime
import json
import jsonschema
import os
import tempfile

import sarif
from sarif.operations import copy_op
from sarif import sarif_file
from tests.utils import get_sarif_schema

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
    sarif_schema = get_sarif_schema()
    input_sarif_file = sarif_file.SarifFile(
        "SARIF_WITH_1_ISSUE", SARIF_WITH_1_ISSUE, mtime=datetime.datetime.now()
    )
    jsonschema.validate(input_sarif_file.data, schema=sarif_schema)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)
    with tempfile.TemporaryDirectory() as tmp:
        output_file_path = os.path.join(tmp, "copied.json")
        output_sarif_file = copy_op.generate_sarif(
            input_sarif_file_set,
            output_file_path,
            append_timestamp=False,
            sarif_tools_version="1.2.3",
            cmdline="unit-test",
        )

        with open(output_file_path, "rb") as f_out:
            output_sarif = json.load(f_out)
        assert output_sarif_file.data == output_sarif
        jsonschema.validate(output_sarif, schema=sarif_schema)

        expected_sarif = deepcopy(input_sarif_file.data)
        conversion = {
            "tool": {
                "driver": {
                    "name": "sarif-tools",
                    "fullName": "sarif-tools https://github.com/microsoft/sarif-tools/",
                    "version": "1.2.3",
                    "properties": {
                        "file": input_sarif_file.abs_file_path,
                        "modified": input_sarif_file.mtime.isoformat(),
                        "processed": output_sarif["runs"][0]["conversion"]["tool"][
                            "driver"
                        ]["properties"]["processed"],
                    },
                }
            },
            "invocation": {
                "commandLine": "unit-test",
                "executionSuccessful": True,
            },
        }
        expected_sarif["runs"][0]["conversion"] = conversion
        assert output_sarif == expected_sarif
