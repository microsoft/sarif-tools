import datetime

from sarif import sarif_file


def _record_description(rule_id, message_text):
    input_sarif = {
        "runs": [
            {
                "tool": {"driver": {"name": "unit test"}},
                "results": [
                    {
                        "ruleId": rule_id,
                        "message": {"text": message_text},
                    }
                ],
            }
        ]
    }

    input_sarif_file = sarif_file.SarifFile(
        "INPUT_SARIF", input_sarif, mtime=datetime.datetime.now()
    )

    records = input_sarif_file.get_records()

    return records[0]["Description"]


def test_record_description_preserves_message_text_after_rule_id():
    assert (
        _record_description(
            "TEST001", "TEST001 Preserve the full text after the rule id"
        )
        == "Preserve the full text after the rule id"
    )


def test_record_description_keeps_message_that_does_not_start_with_rule_id():
    assert (
        _record_description("TEST001", "Preserve text without a rule id prefix")
        == "Preserve text without a rule id prefix"
    )


def test_record_description_keeps_exact_rule_id_message():
    assert _record_description("TEST001", "TEST001") == "TEST001"
