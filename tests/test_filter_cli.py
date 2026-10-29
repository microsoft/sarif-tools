import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from sarif.cmdline import main as cmdline_main


def test_cli_reports_filter_configuration_error_without_traceback(tmp_path):
    input_path = tmp_path / "input.sarif"
    input_path.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "unit test"}},
                        "results": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    filter_path = tmp_path / "filter.yaml"
    filter_path.write_text("include:\n  ruleId: R1\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sarif",
            "summary",
            "--filter",
            str(filter_path),
            str(input_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert "include[0] must be a non-empty mapping" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert "AttributeError" not in completed.stderr


def test_cli_reports_malformed_yaml_without_traceback(tmp_path):
    input_path = tmp_path / "input.sarif"
    input_path.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "unit test"}},
                        "results": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    filter_path = tmp_path / "malformed.yaml"
    filter_path.write_text("include: [\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sarif",
            "summary",
            "--filter",
            str(filter_path),
            str(input_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "Invalid filter configuration" in completed.stderr
    assert str(filter_path) in completed.stderr
    for implementation_detail in (
        "Traceback",
        "ParserError",
        "YAMLError",
        "OSError",
        "IOError",
    ):
        assert implementation_detail not in completed.stderr


def test_cli_does_not_hide_unrelated_programming_error(monkeypatch):
    def fail_with_programming_error(_args):
        raise AttributeError("unrelated programming failure")

    args = SimpleNamespace(
        debug=False,
        version=False,
        func=fail_with_programming_error,
    )
    monkeypatch.setattr(
        cmdline_main.ARG_PARSER,
        "parse_known_args",
        lambda: (args, []),
    )

    with pytest.raises(AttributeError, match="unrelated programming failure"):
        cmdline_main.main()
