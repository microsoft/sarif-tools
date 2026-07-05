import datetime

from sarif import sarif_file


def test_record_description_preserves_message_text_after_rule_id():
    input_sarif = {
        "runs": [
            {
                "tool": {"driver": {"name": "unit test"}},
                "results": [
                    {
                        "ruleId": "TEST001",
                        "message": {
                            "text": "TEST001 Preserve the full text after the rule id"
                        },
                    }
                ],
            }
        ]
    }

    input_sarif_file = sarif_file.SarifFile(
        "INPUT_SARIF", input_sarif, mtime=datetime.datetime.now()
    )

    records = input_sarif_file.get_records()

    assert records[0]["Description"] == "Preserve the full text after the rule id"
