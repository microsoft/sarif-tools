import pathlib

import sarif


def test_version():
    with open(pathlib.Path(__file__).parent.parent / "pyproject.toml") as pyproject_in:
        for pyproject_line in pyproject_in.readlines():
            if pyproject_line.startswith("version = \""):
                assert pyproject_line.strip() == f"version = \"{sarif.__version__}\""
