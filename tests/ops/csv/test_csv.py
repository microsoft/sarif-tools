import datetime
import os
import tempfile

from sarif.operations import csv_op
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


EXPECTED_OUTPUT_CSV = [
    "Tool,Severity,Code,Description,Location,Line",
    "unit test,error,CA2101,CA2101,file:///C:/Code/main.c,24",
]


def test_csv():
    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("INPUT_SARIF", INPUT_SARIF, mtime=mtime)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "output.csv")
        csv_op.generate_csv(
            input_sarif_file_set, file_path, output_multiple_files=False
        )

        with open(file_path, "rb") as f_in:
            output_lines = f_in.read().decode().splitlines()

        assert output_lines == EXPECTED_OUTPUT_CSV
