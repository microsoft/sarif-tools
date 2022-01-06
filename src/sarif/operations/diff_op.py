"""
Code for `sarif diff` command.
"""

import json
import sys
from typing import Dict

from sarif.sarif_file import SarifFileSet, SARIF_SEVERITIES


def _occurrences(occurrence_count):
    return "1 occurence" if occurrence_count == 1 else f"{occurrence_count} occurrences"


def _signed_change(difference):
    return str(difference) if difference < 0 else f"+{difference}"


def print_diff(
    original_sarif: SarifFileSet, new_sarif: SarifFileSet, output, check_level=None
) -> str:
    """
    Generate a diff of the issues from the SARIF files and write it to stdout
    or a file if specified.
    original_sarif corresponds to the old files.
    new_sarif corresponds to the new files.
    """
    diff = calc_diff(original_sarif, new_sarif)
    if output:
        print("writing diff to", output)
        with open(output, "w", encoding="utf-8") as output_file:
            json.dump(diff, output_file, indent=4)
    else:
        for severity in SARIF_SEVERITIES:
            if diff[severity]["codes"]:
                print(
                    severity,
                    "level:",
                    _signed_change(diff[severity]["+"]),
                    _signed_change(-diff[severity]["-"]),
                )
                for (issue_code, old_count, new_count) in diff[severity]["codes"]:
                    if old_count == 0:
                        print(f'  New issue "{issue_code}" ({_occurrences(new_count)})')
                    elif new_count == 0:
                        print(f'  Eliminated issue "{issue_code}"')
                    else:
                        print(
                            f"  Number of occurrences {old_count} -> {new_count}",
                            f'({_signed_change(new_count - old_count)}) for issue "{issue_code}"',
                        )
            else:
                print(severity, "level: +0 -0 no changes")
        print(
            "all levels:",
            _signed_change(diff["all"]["+"]),
            _signed_change(-diff["all"]["-"]),
        )
    filter_stats = original_sarif.get_filter_stats()
    if filter_stats:
        print(f"  'Before' results were filtered by {filter_stats}")
    filter_stats = new_sarif.get_filter_stats()
    if filter_stats:
        print(f"  'After' results were filtered by {filter_stats}")
    ret = 0
    if check_level:
        for severity in SARIF_SEVERITIES:
            ret += diff.get(severity, {}).get("+", 0)
            if severity == check_level:
                break
    if ret > 0:
        sys.stderr.write(
            f"Check: exiting with return code {ret} due to increase in issues at or above {check_level} severity\n"
        )
    return ret


def calc_diff(original_sarif: SarifFileSet, new_sarif: SarifFileSet) -> Dict:
    """
    Generate a diff of the issues from the SARIF files.
    original_sarif corresponds to the old files.
    new_sarif corresponds to the new files.
    Return dict has keys "error", "warning", "note" and "all".
    """
    ret = {"all": {"+": 0, "-": 0}}
    for severity in SARIF_SEVERITIES:
        original_histogram = dict(original_sarif.get_issue_code_histogram(severity))
        new_histogram = new_sarif.get_issue_code_histogram(severity)
        new_histogram_dict = dict(new_histogram)
        ret[severity] = {"+": 0, "-": 0, "codes": []}
        if original_histogram != new_histogram_dict:
            for (issue_code, count) in new_histogram:
                old_count = original_histogram.pop(issue_code, 0)
                if old_count != count:
                    ret[severity]["codes"].append((issue_code, old_count, count))
                    if old_count == 0:
                        ret[severity]["+"] += 1
            for (issue_code, old_count) in original_histogram.items():
                ret[severity]["codes"].append((issue_code, old_count, 0))
                ret[severity]["-"] += 1
        ret["all"]["+"] += ret[severity]["+"]
        ret["all"]["-"] += ret[severity]["-"]
    return ret
