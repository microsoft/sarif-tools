import datetime
import os
import tempfile

from docx import Document
from sarif.operations import word_op
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


EXPECTED_OUTPUT_TXT = [
    "Sarif Summary: unit test",
    "Document generated on: <date_val>",
    "Total number of various severities (error, warning, note): 1",
    "",
    "",
    "Severity : error [ 1 ]",
    "CA2101: 1",
    "Severity : warning [ 0 ]",
    "None",
    "Severity : note [ 0 ]",
    "None",
    "",
    "Severity : error",
    "Severity : warning",
    "None",
    "Severity : note",
    "None",
]


def test_word():
    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("INPUT_SARIF", INPUT_SARIF, mtime=mtime)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        output_file_path = os.path.join(tmp, "output.docx")
        word_op.generate_word_docs_from_sarif_inputs(
            input_sarif_file_set,
            None,
            output_file_path,
            output_multiple_files=False,
            date_val=mtime,
        )

        word_doc = Document(output_file_path)
        word_doc_text = [paragraph.text for paragraph in word_doc.paragraphs]

        assert len(word_doc_text) == len(EXPECTED_OUTPUT_TXT)
        for actual, expected in zip(word_doc_text, EXPECTED_OUTPUT_TXT):
            assert actual == expected.replace(
                "<date_val>", mtime.strftime("%Y-%m-%d %H:%M:%S.%f")
            )
