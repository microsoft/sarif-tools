"""
Code to load SARIF files from disk.
"""

import json
import os

from sarif.sarif_file import has_sarif_file_extension, SarifFile, SarifFileSet


def load_sarif_files(*args) -> SarifFileSet:
    """
    Load SARIF files specified as individual filenames or directories.  Return a SarifFileSet
    object.
    """
    ret = SarifFileSet()
    if args:
        for path in args:
            if os.path.isdir(path):
                ret.add_dir(_load_dir(path))
            elif os.path.isfile(path):
                ret.add_file(load_sarif_file(path))
    return ret


def _load_dir(path):
    subdir = SarifFileSet()
    for (dirpath, _dirnames, filenames) in os.walk(path):
        for filename in filenames:
            if has_sarif_file_extension(filename):
                subdir.add_file(load_sarif_file(os.path.join(dirpath, filename)))
    return subdir


def load_sarif_file(file_path: str) -> SarifFile:
    """
    Load JSON data from a file and return as a SarifFile object.
    As per https://tools.ietf.org/id/draft-ietf-json-rfc4627bis-09.html#rfc.section.8.1, JSON
    data SHALL be encoded in utf-8.
    """
    with open(file_path, encoding="utf-8") as file_in:
        data = json.load(file_in)
    return SarifFile(file_path, data)
