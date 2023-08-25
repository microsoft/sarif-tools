# Contributing

This project welcomes contributions and suggestions. Most contributions require you to
agree to a Contributor License Agreement (CLA) declaring that you have the right to,
and actually do, grant us the rights to use your contribution. For details, visit
https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need
to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the
instructions provided by the bot. You will only need to do this once across all repositories using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Pull Requests

Pull requests are welcome.

1. Fork the repository.
2. Make and test your changes (see Developer Guide below).
3. Run `poetry run black sarif` to format the code.
4. Run `poetry run pylint sarif` and check for no new errors or warnings.
5. Raise Pull Request in GitHub.com.

## Developer Guide

### Prerequisites

- You need Python 3.8 installed.
  - This is the minimum supported version of the tool.  Developing with a later version risks introducing type hints such as `list[dict]` that are not compatible with Python 3.8.
- You need Poetry installed.  Run this in an Admin CMD or under `sudo`:
  - `pip install poetry`

Initialise Poetry by telling it where Python 3.8 is, e.g.

```bash
# Windows - adjust to the path where you have installed Python 3.8.
poetry env use "C:\Python38\python.exe"
# Linux
poetry env use 3.8
```

This is not necessary if your system Python version is 3.8.

### Running locally in Poetry virtualenv

```bash
poetry install
poetry run sarif <OPTIONS>
```

To check that the right versions are being run:

```bash
poetry run python --version
poetry run sarif --version
poetry run python -m sarif --version
```

To see which executable is being run:

```bash
# Windows
poetry run cmd /c "where sarif"
# Linux
poetry run which sarif
```

### Update dependency versions

Run `poetry update` to bump package versions in the `poetry.lock` file.

### Update product version

Change the `version =` line in `pyproject.toml` for the new semantic version for your change.

To make sure you're paying attention, you need to change it in the test `test_version.py` as well.

### Run unit tests

```bash
poetry run pytest
```

### Package using `poetry build`

Run it on the source code:

```bash
poetry build
```

If you want, you can install the package built locally at system level (outside the Poetry virtual environment):

```bash
pip install dist/sarif-*.whl
```

To remove it again:

```bash
pip uninstall sarif-tools
```

Note that there are two possible levels of installation:

#### User installation

When you run `pip install` and `pip` doesn't have permissions to write to the Python installation's `site-packages` directory, probably because you are not running as an admin/superuser, the package is installed at "user" level only.  You can run it using:

```bash
python -m sarif
```

You *cannot* run it using the bare command `sarif`, unless you add your user-level `Scripts` directory to your `PATH`.  You can see where that is in the output from `pip install`:

```plain
Installing collected packages: sarif
  WARNING: The script sarif.exe is installed in 'C:\Users\yournamehere\AppData\Roaming\Python\Python39\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

#### System installation

When you run `pip install` and `pip` has permissions to write to the Python installation's `site-packages` directory, and the Python installation's `Scripts` directory is in your path, then you can run the `sarif` command without `python -m`:

```bash
sarif
```

### Adding packages from pypi to the project

Add the package and its latest version number (as minimum version) to `[tool.poetry.dependencies]` in `pyproject.toml`.

Then run this to update Poetry's lockfile.

```bash
poetry update
```

### Adding resource files to the project

Add the file within the `sarif` directory and it will be installed with the Python source.  For example, `sarif/operations/templates/sarif_summary.html`.
