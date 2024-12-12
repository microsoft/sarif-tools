import datetime
import os
import tempfile

from sarif.operations import emacs_op
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


EXPECTED_OUTPUT_TXT = """-*- compilation -*-

Sarif Summary: unit test
Document generated on: <date_val>
Total number of distinct issues of all severities (error, warning, note): 1



Severity : error [1]
file:///C:/Code/main.c:24: CA2101



Severity : warning [0]


Severity : note [0]

"""


def test_emacs():
    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("INPUT_SARIF", INPUT_SARIF, mtime=mtime)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "output.csv")
        emacs_op.generate_compile(
            input_sarif_file_set, file_path, output_multiple_files=False, date_val=mtime
        )

        with open(file_path, "rb") as f_in:
            output = f_in.read().decode()

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep).replace(
            "<date_val>", mtime.strftime("%Y-%m-%d %H:%M:%S.%f")
        )
