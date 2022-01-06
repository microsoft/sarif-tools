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

# Pull Requests

Pull requests are welcome.
1. Fork the repository.
2. Make and test your changes (see Developer Guide below).
3. Run `python -m black .` to format the code (`python -m pip install black` if necessary).
4. Run `python -m pylint src` and check for no new errors or warnings (`python -m pip install pylint` if necessary).
5. Raise Pull Request in GitHub.com.

# Developer Guide

## Prerequisites

- You need Python 3.8 installed.
  - This is the minimum supported version of the tool.  Developing with a later version risks introducing type hints such as `list[dict]` that are not compatible with Python 3.8.

## Running without installing

Use `run.py`.  E.g.
```
python run.py ls "C:\temp\sarif_files"
```

## Package using `build`

Install the [build](https://pypi.org/project/build/) package:
```
python -m pip install --upgrade build
```

Run it on the source code:
```
python -m build
```

Install the package built by `build` locally:
```
python -m pip install dist/sarif-*.whl
```

## Install locally using `setuptools`

Run this in the base directory:
```
python -m pip install .
```
`pip` uses a small shim `setup.py` to invoke `setuptools`.  Then `setuptools` installs all runtime requirements and also installs `sarif`.

Note that there are two possible levels of installation:

### User installation
When you run `pip install` and `pip` doesn't have permissions to write to the Python installation's `site-packages` directory, probably because you are not running as an admin/superuser, the package is installed at "user" level only.  You can run it using:
```
python -m sarif
```
You *cannot* run it using the bare command `sarif`, unless you add your user-level `Scripts` directory to your `PATH`.  You can see where that is in the output from `pip install`:
```
Installing collected packages: sarif
  WARNING: The script sarif.exe is installed in 'C:\Users\yournamehere\AppData\Roaming\Python\Python39\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

### System installation
When you run `pip install` and `pip` has permissions to write to the Python installation's `site-packages` directory, and the Python installation's `Scripts` directory is in your path, then you can run the `sarif` command without `python -m`:
```
sarif
```

## Running locally-installed sarif-tools

Run the installed package using the `python -m sarif` command:
```
python -m sarif ls "C:\temp\sarif_files"
```
If installed at system level, you can alternatively run the installed package using the `sarif command`.
```
sarif ls "C:\temp\sarif_files"
```

## Adding packages from pypi to the project

Add the package and its version to `install_requires` in `setup.cfg`.

Then run this in the base directory to install the tool and all its requirements locally:
```
pip install .
```

You can also run `pip install <packagename>` before or after this, as you wish.  But you need to add the dependency to `setup.cfg` to make sure that the packaged application depends on this dependency when other people install it.

## Adding resource files to the project

Add the glob to `MANIFEST.in`.  This is read because `include_package_data` in `setup.cfg` is `True`.
