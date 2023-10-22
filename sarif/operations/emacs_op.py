"""
Code for `sarif emacs` command.
"""

from datetime import datetime
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sarif import sarif_file

_THIS_MODULE_PATH = os.path.dirname(__file__)

_TEMPLATES_PATH = os.path.join(_THIS_MODULE_PATH, "templates")

_ENV = Environment(
    loader=FileSystemLoader(searchpath=_TEMPLATES_PATH),
    autoescape=select_autoescape(),
)


def generate_compile(
    input_files: sarif_file.SarifFileSet, output: str, output_multiple_files: bool
):
    """
    Generate txt file from the input files.
    """
    date_val = datetime.now()

    output_file = output
    if output_multiple_files:
        for input_file in input_files:
            output_file_name = input_file.get_file_name_without_extension() + ".txt"
            print(
                "Writing results for",
                input_file.get_file_name(),
                "to",
                output_file_name,
            )
            _generate_single_txt(
                input_file, os.path.join(output, output_file_name), date_val
            )
        output_file = os.path.join(output, ".compile.txt")
    source_description = input_files.get_description()
    print(
        "Writing results for",
        source_description,
        "to",
        os.path.basename(output_file),
    )
    _generate_single_txt(input_files, output_file, date_val)


def _generate_single_txt(input_file, output_file, date_val):
    all_tools = input_file.get_distinct_tool_names()

    total_distinct_issue_codes = 0
    problems = []

    issues_by_severity = input_file.get_records_grouped_by_severity()
    for severity, issues_of_severity in issues_by_severity.items():
        issue_code_histogram = input_file.get_issue_code_histogram(severity)

        distinct_issue_codes = len(issue_code_histogram)
        total_distinct_issue_codes += distinct_issue_codes

        severity_details = _enrich_details(issue_code_histogram, issues_of_severity)

        severity_section = {
            "type": severity,
            "count": distinct_issue_codes,
            "details": severity_details,
        }

        problems.append(severity_section)

    filtered = None
    filter_stats = input_file.get_filter_stats()
    if filter_stats:
        filtered = f"Results were filtered by {filter_stats}."

    template = _ENV.get_template("sarif_emacs.txt")
    txt_content = template.render(
        report_type=", ".join(all_tools),
        report_date=date_val,
        severities=", ".join(issues_by_severity.keys()),
        total=total_distinct_issue_codes,
        problems=problems,
        filtered=filtered,
    )

    with open(output_file, "wt", encoding="utf-8") as file_out:
        file_out.write(txt_content)


def _enrich_details(histogram, records_of_severity):
    enriched_details = []

    for error_code_and_desc, count in histogram:
        error_lines = [
            e
            for e in records_of_severity
            if sarif_file.combine_code_and_description(e) == error_code_and_desc
        ]
        lines = sorted(
            error_lines, key=lambda x: x["Location"] + str(x["Line"]).zfill(6)
        )
        enriched_details.append(
            {"code": error_code_and_desc, "count": count, "details": lines}
        )
    return enriched_details
