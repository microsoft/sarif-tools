"""
This is a shim to allow `pip` to install the dependencies listed in `setup.cfg`.
Based on idea https://stackoverflow.com/a/61762525/316578.

To install all required dependencies:
```
pip install .
```
"""
from setuptools import setup

setup()
