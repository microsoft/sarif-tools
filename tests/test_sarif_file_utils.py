from sarif import sarif_file_utils


def test_combine_code_and_description_short():
    cd = sarif_file_utils.combine_code_and_description(
        "ABC123", "Some short description"
    )
    assert cd == "ABC123 Some short description"
    assert len(cd) <= 120


def test_combine_code_and_description_long_desc():
    cd = sarif_file_utils.combine_code_and_description(
        "ABC123", " ".join(f"blah{i}" for i in range(1, 30))
    )
    assert (
        cd
        == "ABC123 blah1 blah2 blah3 blah4 blah5 blah6 blah7 blah8 blah9 blah10 blah11 blah12 blah13 blah14 blah15 blah16 ..."
    )
    assert len(cd) <= 120


def test_combine_code_and_description_long_code():
    long_code = "".join(f"A{i}" for i in range(1, 36)) + "BC"
    assert (
        len(long_code) == 98
    ), "98 is right length to hit 'placeholder too large for max width' without defensive code"
    cd = sarif_file_utils.combine_code_and_description(
        long_code, "wow that's a long code"
    )
    assert cd == f"{long_code} wow that's a ..."
    assert len(cd) <= 120
    long_code = "".join(f"A{i}" for i in range(1, 50))
    cd = sarif_file_utils.combine_code_and_description(
        long_code, "wow that's a long code"
    )
    assert cd == long_code


def test_read_result_rule():
    run = {"tool":
           {"driver":
            {"rules": [
                {"id": "id0", "defaultConfiguration": {"level": "none"}},
                {"id": "id1", "defaultConfiguration": {"level": "error"}}
             ]}}}
    rule_id0 = run["tool"]["driver"]["rules"][0]
    rule_id1 = run["tool"]["driver"]["rules"][1]

    result = {}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule is None
    assert ruleIndex == -1

    result = {"ruleIndex": 1}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule == rule_id1
    assert ruleIndex == 1

    result = {"rule": { "index": 1}}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule == rule_id1
    assert ruleIndex == 1

    result = {"ruleId": "id1"}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule == rule_id1
    assert ruleIndex == 1

    result = {"rule": { "id": "id1"}}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule == rule_id1
    assert ruleIndex == 1

    result = {"ruleIndex": 0}
    (rule, ruleIndex) = sarif_file_utils.read_result_rule(result, run)
    assert rule == rule_id0
    assert ruleIndex == 0


def test_read_result_severity():
    result = {"level": "error"}
    severity = sarif_file_utils.read_result_severity(result, {})
    assert severity == "error"

    # If kind has any value other than "fail", then if level is absent, it SHALL default to "none"...
    result = {"kind": "other"}
    severity = sarif_file_utils.read_result_severity(result, {})
    assert severity == "none"

    run = {"invocations": [
             {"ruleConfigurationOverrides": [ {"descriptor": {"id": "id1"}, "configuration": {"level": "note"}} ]},
             {"ruleConfigurationOverrides": [ {"descriptor": {"index": 1}, "configuration": {"level": "note"}} ]},
             { }
           ],
           "tool":
             {"driver":
               {"rules": [
                 {"id": "id0", "defaultConfiguration": {"level": "none"}},
                 {"id": "id1", "defaultConfiguration": {"level": "error"}}
               ]}
             }
           }

    # If kind has the value "fail" and level is absent, then level SHALL be determined by the following procedure:
    # IF rule is present THEN
    #   LET theDescriptor be the reportingDescriptor object that it specifies.
    #   # Is there a configuration override for the level property?
    #   IF result.provenance.invocationIndex is >= 0 THEN
    #     LET theInvocation be the invocation object that it specifies.
    #     IF theInvocation.ruleConfigurationOverrides is present
    #         AND it contains a configurationOverride object whose
    #         descriptor property specifies theDescriptor THEN
    #       LET theOverride be that configurationOverride object.
    #       IF theOverride.configuration.level is present THEN
    #         Set level to theConfiguration.level.
    result = {"ruleIndex": 1, "provenance": {"invocationIndex": 0}}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "note"

    result = {"ruleIndex": 1, "provenance": {"invocationIndex": 1}}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "note"

    #   ELSE
    #     # There is no configuration override for level. Is there a default configuration for it?
    #     IF theDescriptor.defaultConfiguration.level is present THEN
    #       SET level to theDescriptor.defaultConfiguration.level.

    result = {"ruleIndex": 1}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "error"

    result = {"rule": { "index": 1}}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "error"

    result = {"ruleId": "id1"}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "error"

    result = {"rule": { "id": "id1"}}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "error"

    result = {"ruleIndex": 1, "provenance": {"invocationIndex": 2}}
    severity = sarif_file_utils.read_result_severity(result, run)
    assert severity == "error"

    # IF level has not yet been set THEN
    #   SET level to "warning".
    result = {}
    severity = sarif_file_utils.read_result_severity(result, {})
    assert severity == "warning"
