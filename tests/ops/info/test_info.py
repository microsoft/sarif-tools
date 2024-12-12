import datetime
import json
import os
import tempfile

from sarif.operations import info_op
from sarif import sarif_file

INPUT_SARIF = """{
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
                                    "index": 0
                                },
                                "region": {"startLine": 24, "startColumn": 9}
                            }
                        }
                    ]
                }
            ]
        }
    ]
}
"""

EXPECTED_OUTPUT_TXT = """<path>
  840 bytes (1 KiB)
  modified: <time>, accessed: <time>, ctime: <time>
  1 run
    Tool: unit test
    1 result

"""


def test_info():
    with tempfile.TemporaryDirectory() as tmp:
        input_sarif_file_path = os.path.join(tmp, "input.sarif")
        with open(input_sarif_file_path, "wb") as f_in:
            f_in.write(INPUT_SARIF.encode())

        mtime = datetime.datetime.fromtimestamp(os.stat(input_sarif_file_path).st_mtime)

        input_sarif = json.loads(INPUT_SARIF)

        input_sarif_file = sarif_file.SarifFile(
            input_sarif_file_path, input_sarif, mtime=datetime.datetime.now()
        )

        input_sarif_file_set = sarif_file.SarifFileSet()
        input_sarif_file_set.files.append(input_sarif_file)

        file_path = os.path.join(tmp, "output.txt")
        info_op.generate_info(input_sarif_file_set, file_path)

        with open(file_path, "rb") as f_out:
            output = f_out.read().decode()

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep).replace(
            "<path>", input_sarif_file_path
        ).replace(
            "<time>",
            mtime.strftime("%Y-%m-%d %H:%M:%S.%f"),
        )
