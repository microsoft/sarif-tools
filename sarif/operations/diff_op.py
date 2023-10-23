"""
Code for `sarif diff` command.
"""

import json
import sys
from typing import Dict

from sarif import sarif_file


def _occurrences(occurrence_count):
    return (
        "1 occurrence" if occurrence_count == 1 else f"{occurrence_count} occurrences"
    )


def _signed_change(difference):
    return str(difference) if difference < 0 else f"+{difference}"


def _record_to_location_tuple(record) -> str:
    return (record["Location"], record["Line"])


def print_diff(
    original_sarif: sarif_file.SarifFileSet,
    new_sarif: sarif_file.SarifFileSet,
    output,
    check_level=None,
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
        for severity in sarif_file.SARIF_SEVERITIES:
            if diff[severity]["codes"]:
                print(
                    severity,
                    "level:",
                    _signed_change(diff[severity]["+"]),
                    _signed_change(-diff[severity]["-"]),
                )
                for issue_code, code_info in diff[severity]["codes"].items():
                    (old_count, new_count, new_locations) = (
                        code_info["<"],
                        code_info[">"],
                        code_info.get("+@", []),
                    )
                    if old_count == 0:
                        print(f'  New issue "{issue_code}" ({_occurrences(new_count)})')
                    elif new_count == 0:
                        print(f'  Eliminated issue "{issue_code}"')
                    else:
                        print(
                            f"  Number of occurrences {old_count} -> {new_count}",
                            f'({_signed_change(new_count - old_count)}) for issue "{issue_code}"',
                        )
                    if new_locations:
                        # Print the top 3 new locations
                        for record in new_locations[0:3]:
                            (location, line) = _record_to_location_tuple(record)
                            print(f"    {location}:{line}")
                        if len(new_locations) > 3:
                            print("    ...")
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
        for severity in sarif_file.SARIF_SEVERITIES:
            ret += diff.get(severity, {}).get("+", 0)
            if severity == check_level:
                break
    if ret > 0:
        sys.stderr.write(
            f"Check: exiting with return code {ret} due to increase in issues at or above {check_level} severity\n"
        )
    return ret


def _find_new_occurrences(new_records, old_records, issue_code_and_desc):
    old_occurrences = [
        r
        for r in old_records
        if sarif_file.combine_code_and_description(r) == issue_code_and_desc
    ]
    new_occurrences_new_locations = []
    new_occurrences_new_lines = []
    for r in new_records:
        if sarif_file.combine_code_and_description(r) == issue_code_and_desc:
            (new_location, new_line) = (True, True)
            for old_r in old_occurrences:
                if old_r["Location"] == r["Location"]:
                    new_location = False
                    if old_r["Line"] == r["Line"]:
                        new_line = False
                        break
            if new_location:
                if r not in new_occurrences_new_locations:
                    new_occurrences_new_locations.append(r)
            elif new_line:
                if r not in new_occurrences_new_lines:
                    new_occurrences_new_lines.append(r)

    return sorted(
        new_occurrences_new_locations, key=_record_to_location_tuple
    ) + sorted(new_occurrences_new_lines, key=_record_to_location_tuple)


def calc_diff(
    original_sarif: sarif_file.SarifFileSet, new_sarif: sarif_file.SarifFileSet
) -> Dict:
    """
    Generate a diff of the issues from the SARIF files.
    original_sarif corresponds to the old files.
    new_sarif corresponds to the new files.
    Return dict has keys "error", "warning", "note" and "all".
    """
    ret = {"all": {"+": 0, "-": 0}}
    for severity in sarif_file.SARIF_SEVERITIES:
        original_histogram = dict(original_sarif.get_issue_code_histogram(severity))
        new_histogram = new_sarif.get_issue_code_histogram(severity)
        new_histogram_dict = dict(new_histogram)
        ret[severity] = {"+": 0, "-": 0, "codes": {}}
        if original_histogram != new_histogram_dict:
            for issue_code, count in new_histogram:
                old_count = original_histogram.pop(issue_code, 0)
                if old_count != count:
                    ret[severity]["codes"][issue_code] = {"<": old_count, ">": count}
                    if old_count == 0:
                        ret[severity]["+"] += 1
                    new_occurrences = _find_new_occurrences(
                        new_sarif.get_records(),
                        original_sarif.get_records(),
                        issue_code,
                    )
                    if new_occurrences:
                        ret[severity]["codes"][issue_code]["+@"] = [
                            {"Location": r["Location"], "Line": r["Line"]}
                            for r in new_occurrences
                        ]
            for issue_code, old_count in original_histogram.items():
                ret[severity]["codes"][issue_code] = {"<": old_count, ">": 0}
                ret[severity]["-"] += 1
        ret["all"]["+"] += ret[severity]["+"]
        ret["all"]["-"] += ret[severity]["-"]
    return ret
