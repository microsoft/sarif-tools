"""
Code for `sarif summary` command.
"""

import os
from typing import List

from sarif import sarif_file
from sarif.sarif_file import SarifFileSet


def generate_summary(
    input_files: SarifFileSet, output: str, output_multiple_files: bool
):
    """
    Generate a summary of the issues from the SARIF files.
    sarif_dict is a dict from filename to deserialized SARIF data.
    output_file is the name of a text file to write, or if None, the summary is written to the
    console.
    """
    output_file = output
    if output_multiple_files:
        for input_file in input_files:
            output_file_name = (
                input_file.get_file_name_without_extension() + "_summary.txt"
            )
            output_file = os.path.join(output, output_file_name)
            summary_lines = _generate_summary(input_file)
            print(
                "Writing summary of",
                input_file.get_file_name(),
                "to",
                output_file_name,
            )
            with open(output_file, "w", encoding="utf-8") as file_out:
                file_out.writelines(l + "\n" for l in summary_lines)
        output_file_name = "static_analysis_summary.txt"
        output_file = os.path.join(output, output_file_name)

    summary_lines = _generate_summary(input_files)
    if output:
        print(
            "Writing summary of",
            input_files.get_description(),
            "to",
            output_file,
        )
        with open(output_file, "w", encoding="utf-8") as file_out:
            file_out.writelines(l + "\n" for l in summary_lines)
    else:
        for lstr in summary_lines:
            print(lstr)


def _generate_summary(input_files: SarifFileSet) -> List[str]:
    """
    For each severity level (in priority order): create a list of the errors of
    that severity, print out how many there are and then do some further analysis
    of which error codes are present.
    """
    ret = []
    result_count_by_severity = input_files.get_result_count_by_severity()
    for severity in sarif_file.SARIF_SEVERITIES:
        issue_code_histogram = input_files.get_issue_code_histogram(severity)
        result_count = result_count_by_severity.get(severity, 0)
        ret.append(f"\n{severity}: {result_count}")
        ret += [f" - {code}: {count}" for (code, count) in issue_code_histogram]
    filter_stats = input_files.get_filter_stats()
    if filter_stats:
        ret.append(f"\nResults were filtered by {filter_stats}")
    return ret
