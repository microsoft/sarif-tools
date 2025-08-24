"""
Test for the HTML autotrim bug fix (issue #85).
"""
import datetime
import os
import tempfile

from sarif.operations import html_op
from sarif import sarif_file


def test_autotrim_respects_directory_boundaries():
    """Test that autotrim doesn't break directory boundaries when trimming common prefixes."""
    
    # Create test SARIF data with paths that have a common prefix but not at directory boundary
    INPUT_SARIF = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "test tool",
                        "rules": [
                            {
                                "id": "CKV_SECRET_3",
                                "name": "Azure Storage Account access key",
                            }
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": "CKV_SECRET_3",
                        "level": "error",
                        "message": {"text": "Azure Storage Account access key"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": "tools/bin/RedacteA/RedacteB/RedacteB.deps.json",
                                    },
                                    "region": {"startLine": 953},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "CKV_SECRET_3",
                        "level": "error",
                        "message": {"text": "Azure Storage Account access key"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": "tools/bin/RedacteC/RedacteD/RedacteD.deps.json",
                                    },
                                    "region": {"startLine": 960},
                                }
                            }
                        ],
                    },
                ],
            }
        ],
    }

    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("test.sarif", INPUT_SARIF, mtime=mtime)
    input_sarif_file.init_path_prefix_stripping(autotrim=True)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "output.html")
        html_op.generate_html(
            input_sarif_file_set,
            None,
            file_path,
            output_multiple_files=False,
            date_val=mtime,
        )

        with open(file_path, "rb") as f_in:
            output = f_in.read().decode()
        
        # Verify that the bug is fixed - should NOT contain broken paths
        bad_patterns = ["ools/bin", ">A/RedacteB/RedacteB.deps.json", ">C/RedacteD/RedacteD.deps.json"]
        for pattern in bad_patterns:
            assert pattern not in output, f"Found incorrectly trimmed path: {pattern}"
        
        # Should contain the properly trimmed paths
        assert "RedacteA/RedacteB/RedacteB.deps.json" in output, "Properly trimmed path not found"
        assert "RedacteC/RedacteD/RedacteD.deps.json" in output, "Properly trimmed path not found"


def test_autotrim_no_common_prefix():
    """Test that autotrim works correctly when there's no common directory prefix."""
    
    INPUT_SARIF = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "test tool",
                        "rules": [{"id": "TEST_RULE", "name": "Test Rule"}],
                    }
                },
                "results": [
                    {
                        "ruleId": "TEST_RULE",
                        "level": "error",
                        "message": {"text": "Test message"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/file1.java"},
                                    "region": {"startLine": 1},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "TEST_RULE",
                        "level": "error",
                        "message": {"text": "Test message"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "test/file2.java"},
                                    "region": {"startLine": 2},
                                }
                            }
                        ],
                    },
                ],
            }
        ],
    }

    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("test.sarif", INPUT_SARIF, mtime=mtime)
    input_sarif_file.init_path_prefix_stripping(autotrim=True)

    # Check that no prefix was set (no common directory prefix)
    assert input_sarif_file.runs[0]._path_prefixes_upper is None

    # Check that the paths are unchanged
    records = input_sarif_file.get_records()
    assert records[0]["Location"] == "src/file1.java"
    assert records[1]["Location"] == "test/file2.java"


def test_autotrim_proper_directory_prefix():
    """Test that autotrim works correctly with a proper common directory prefix."""
    
    INPUT_SARIF = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "test tool",
                        "rules": [{"id": "TEST_RULE", "name": "Test Rule"}],
                    }
                },
                "results": [
                    {
                        "ruleId": "TEST_RULE",
                        "level": "error",
                        "message": {"text": "Test message"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/main/file1.java"},
                                    "region": {"startLine": 1},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "TEST_RULE",
                        "level": "error",
                        "message": {"text": "Test message"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/main/file2.java"},
                                    "region": {"startLine": 2},
                                }
                            }
                        ],
                    },
                ],
            }
        ],
    }

    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("test.sarif", INPUT_SARIF, mtime=mtime)
    input_sarif_file.init_path_prefix_stripping(autotrim=True)

    # Check that the proper prefix was set
    assert input_sarif_file.runs[0]._path_prefixes_upper == ["SRC/MAIN/"]

    # Check that the paths are properly trimmed
    records = input_sarif_file.get_records()
    assert records[0]["Location"] == "file1.java"
    assert records[1]["Location"] == "file2.java"