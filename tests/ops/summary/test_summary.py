import datetime
import json
import os
import tempfile

from sarif.operations import summary_op
from sarif import sarif_file

INPUT_SARIF = """{
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "CA2103",
                    "level": "error"
                },
                {
                    "ruleId": "CA2102",
                    "level": "warning"
                },
                {
                    "ruleId": "CA2101",
                    "level": "warning"
                },
                {
                    "ruleId": "CA2101",
                    "level": "error"
                },
                {
                    "ruleId": "CA2101",
                    "level": "note"
                },
                {
                    "ruleId": "CA2101",
                    "level": "none"
                },
                {
                    "ruleId": "CA2101",
                    "level": "error"
                }
            ]
        }
    ]
}
"""

EXPECTED_OUTPUT_TXT = """
error: 3
 - CA2101: 2
 - CA2103: 1

warning: 2
 - CA2102: 1
 - CA2101: 1

note: 1
 - CA2101: 1

none: 1
 - CA2101: 1
"""


def test_summary():
    with tempfile.TemporaryDirectory() as tmp:
        input_sarif_file_path = os.path.join(tmp, "input.sarif")
        with open(input_sarif_file_path, "wb") as f_in:
            f_in.write(INPUT_SARIF.encode())

        input_sarif = json.loads(INPUT_SARIF)

        input_sarif_file = sarif_file.SarifFile(
            input_sarif_file_path, input_sarif, mtime=datetime.datetime.now()
        )

        input_sarif_file_set = sarif_file.SarifFileSet()
        input_sarif_file_set.files.append(input_sarif_file)

        file_path = os.path.join(tmp, "output.txt")
        summary_op.generate_summary(
            input_sarif_file_set, file_path, output_multiple_files=False
        )

        with open(file_path, "rb") as f_out:
            output = f_out.read().decode()

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep)
