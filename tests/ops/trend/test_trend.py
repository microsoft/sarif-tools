import datetime
import json
import os
import tempfile

from sarif.operations import trend_op
from sarif import sarif_file

INPUT_SARIF_1 = """{
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "name 1"}},
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

INPUT_SARIF_2 = """{
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "name 2"}},
            "results": [
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

INPUTS = {
    "trend_test_20250106T060000Z.sarif": INPUT_SARIF_1,
    "trend_test_20250107T060000Z.sarif": INPUT_SARIF_2,
}

EXPECTED_OUTPUT_TXT = """Date,Tool,error,warning,note,none
06/01/2025 06:00,name 1,3,2,1,1
07/01/2025 06:00,name 2,2,0,1,1
"""


def test_trend():
    with tempfile.TemporaryDirectory() as tmp:
        input_sarif_file_set = sarif_file.SarifFileSet()

        for input_file_name, input_json in INPUTS.items():
            input_sarif_file_path = os.path.join(tmp, input_file_name)
            with open(input_sarif_file_path, "wb") as f_in:
                f_in.write(input_json.encode())

            input_sarif = json.loads(input_json)

            input_sarif_file = sarif_file.SarifFile(
                input_sarif_file_path, input_sarif, mtime=datetime.datetime.now()
            )

            input_sarif_file_set.files.append(input_sarif_file)

        file_path = os.path.join(tmp, "output.txt")
        trend_op.generate_trend_csv(input_sarif_file_set, file_path, dateformat="dmy")

        with open(file_path, "rb") as f_out:
            output = f_out.read().decode()

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep)
