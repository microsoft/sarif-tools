"""Test emacs_op module."""

import json
import os
import tempfile
from datetime import datetime

from sarif import sarif_file
from sarif.operations import emacs_op


def test_emacs_output_full_description():
    """Test that emacs output includes full descriptions even for similar warnings."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_file = os.path.join(tmp_dir, "input.sarif")
        output_file = os.path.join(tmp_dir, "output.txt")

        # Create a test SARIF file with similar but different descriptions
        sarif_content = {
            "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "TestTool"
                        }
                    },
                    "results": [
                        {
                            "ruleId": "test/similar-warnings",
                            "message": {
                                "text": "This is a test message with parameter A."
                            },
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": "test/file1.c"
                                        },
                                        "region": {
                                            "startLine": 10
                                        }
                                    }
                                }
                            ]
                        },
                        {
                            "ruleId": "test/similar-warnings",
                            "message": {
                                "text": "This is a test message with parameter B."
                            },
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": "test/file2.c"
                                        },
                                        "region": {
                                            "startLine": 20
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Write the SARIF file
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(sarif_content, f)

        # Generate emacs format output
        input_files = sarif_file.SarifFileSet()
        input_files.add_file(input_file)
        emacs_op._generate_single_txt(input_files, output_file, datetime(2025, 1, 1))

        # Read the output and check it contains full descriptions
        with open(output_file, "r", encoding="utf-8") as f:
            output_content = f.read()

        # Check that the full descriptions are in the output, not truncated
        assert "This is a test message with parameter A." in output_content
        assert "This is a test message with parameter B." in output_content
        assert "This is a test message with parameter ..." not in output_content