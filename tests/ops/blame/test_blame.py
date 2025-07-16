from copy import deepcopy
import datetime
import json
import jsonschema
import os
import tempfile
from typing import Callable, List

from sarif.operations import blame_op
from sarif import sarif_file
from tests.utils import get_sarif_schema

ERROR_FILE_RELATIVE_PATH = "subdir/file.py"
ERROR_FILE_ABSOLUTE_PATH = "file:///C:/repo/subdir/file.py"

SARIF_FILE = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "CA2101",
                    "message": {"text": "just testing"},
                    "level": "error",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": ERROR_FILE_ABSOLUTE_PATH,
                                    "index": 0,
                                },
                                "region": {"startLine": 3, "startColumn": 9},
                            }
                        }
                    ],
                }
            ],
        }
    ],
}

GIT_BLAME_OUTPUT = [
    "f9db03438aba52affc5c3fcdb619afa620ad603a 1 1 7\n",
    "author Taylor Developer\n",
    "author-mail <taylor@developer.com>\n",
    "author-time 1699272533\n",
    "author-tz +0000\n",
    "committer GitHub\n",
    "committer-mail <noreply@github.com>\n",
    "committer-time 1699272533\n",
    "committer-tz +0000\n",
    "summary Commit message 1\n",
    "filename " + ERROR_FILE_RELATIVE_PATH + "\n",
    "\tFile text line 1\n",
    "f9db03438aba52affc5c3fcdb619afa620ad603a 2 2\n",
    "\tFile text line 2\n",
    "f9db03438aba52affc5c3fcdb619afa620ad603a 3 3\n",
    "\tFile text line 3\n",
    "eec0471db074a037d820abdda1f210f8a8c987ca 4 4 1\n",
    "author Other Developer\n",
    "author-mail <other@developer.com>\n",
    "author-time 1718035364\n",
    "author-tz +0100\n",
    "committer GitHub\n",
    "committer-mail <noreply@github.com>\n",
    "committer-time 1718035364\n",
    "committer-tz +0100\n",
    "summary Commit message 2\n",
    "filename " + ERROR_FILE_RELATIVE_PATH + "\n",
    "\tFile text line 4\n",
    "6732313c320314c122bd00aa40e7c79954f21c15 5 5 1\n",
    "author Another Developer\n",
    "author-mail <another@developer.com>\n",
    "author-time 1727710690\n",
    "author-tz -0700\n",
    "committer GitHub\n",
    "committer-mail <noreply@github.com>\n",
    "committer-time 1727710690\n",
    "committer-tz -0700\n",
    "summary Commit message 3\n",
    "filename " + ERROR_FILE_RELATIVE_PATH + "\n",
    "\tFile text line 5\n",
    "6732313c320314c122bd00aa40e7c79954f21c15 6 6\n",
    "\tFile text line 6\n",
]


def test_blame_no_blame_info():
    input_sarif_file = sarif_file.SarifFile(
        "SARIF_FILE", SARIF_FILE, mtime=datetime.datetime.now()
    )
    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        repo_path = os.path.join(tmp, "repo")
        os.makedirs(repo_path)
        output_file_path = os.path.join(tmp, "blamed.json")

        blame_op.enhance_with_blame(
            input_sarif_file_set,
            repo_path,
            output_file_path,
            output_multiple_files=False,
            run_git_blame=lambda repo_path, file_path: [],
        )

        assert not os.path.isfile(output_file_path)


def blame_test(
    run_git_blame: Callable[[str, str], List[bytes]],
    expected_blame_properties: dict[str, dict[str, str]],
):
    input_sarif_file = sarif_file.SarifFile(
        "SARIF_FILE", SARIF_FILE, mtime=datetime.datetime.now()
    )
    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        repo_path = os.path.join(tmp, "repo")
        os.makedirs(repo_path)
        output_file_path = os.path.join(tmp, "blamed.json")

        def run_git_blame_wrapper(
            blame_repo_path: str, blame_file_path: str
        ) -> List[bytes]:
            assert blame_repo_path == repo_path
            assert blame_file_path == ERROR_FILE_ABSOLUTE_PATH
            return run_git_blame(blame_repo_path, blame_file_path)

        blame_op.enhance_with_blame(
            input_sarif_file_set,
            repo_path,
            output_file_path,
            output_multiple_files=False,
            run_git_blame=run_git_blame_wrapper,
        )

        with open(output_file_path, "rb") as f_out:
            output_sarif = json.load(f_out)
        jsonschema.validate(output_sarif, schema=get_sarif_schema())

        expected_sarif = deepcopy(input_sarif_file.data)
        expected_sarif["runs"][0]["results"][0]["properties"] = (
            expected_blame_properties
        )
        assert output_sarif == expected_sarif


def test_blame_success():
    def run_git_blame(blame_repo_path: str, blame_file_path: str) -> List[bytes]:
        return [x.encode() for x in GIT_BLAME_OUTPUT]

    expected_blame_properties = {
        "blame": {
            "author": "Taylor Developer",
            "author-mail": "<taylor@developer.com>",
            "author-time": "1699272533",
            "author-tz": "+0000",
            "committer": "GitHub",
            "committer-mail": "<noreply@github.com>",
            "committer-time": "1699272533",
            "committer-tz": "+0000",
            "summary": "Commit message 1",
            "filename": ERROR_FILE_RELATIVE_PATH,
        }
    }

    blame_test(run_git_blame, expected_blame_properties)


GIT_BLAME_OUTPUT_WITH_INVALID_UTF8 = [
    b"f9db03438aba52affc5c3fcdb619afa620ad603a 1 1 7\n",
    b"author Taylor Developer\n",
    b"author-mail <taylor@developer.com>\n",
    b"author-time 1699272533\n",
    b"author-tz +0000\n",
    b"committer GitHub\n",
    b"committer-mail <noreply@github.com>\n",
    b"committer-time 1699272533\n",
    b"committer-tz +0000\n",
    b"summary Commit message \x80\n",
    b"filename " + ERROR_FILE_RELATIVE_PATH.encode() + b"\n",
    b"\tFile text line 1\n",
    b"f9db03438aba52affc5c3fcdb619afa620ad603a 2 2\n",
    b"\tFile text line 2\n",
    b"f9db03438aba52affc5c3fcdb619afa620ad603a 3 3\n",
    b"\tFile text line 3\n",
    b"eec0471db074a037d820abdda1f210f8a8c987ca 4 4 1\n",
]


def test_blame_invalid_utf8():
    def run_git_blame(blame_repo_path: str, blame_file_path: str) -> List[bytes]:
        return GIT_BLAME_OUTPUT_WITH_INVALID_UTF8

    expected_blame_properties = {
        "blame": {
            "author": "Taylor Developer",
            "author-mail": "<taylor@developer.com>",
            "author-time": "1699272533",
            "author-tz": "+0000",
            "committer": "GitHub",
            "committer-mail": "<noreply@github.com>",
            "committer-time": "1699272533",
            "committer-tz": "+0000",
            "summary": "Commit message �",
            "filename": ERROR_FILE_RELATIVE_PATH,
        }
    }

    blame_test(run_git_blame, expected_blame_properties)
