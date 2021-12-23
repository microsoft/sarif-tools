"""
Code for `sarif html` command.
"""

import base64
from datetime import datetime
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sarif import charts
from sarif.sarif_file import SarifFileSet

_THIS_MODULE_PATH = os.path.dirname(__file__)

_TEMPLATES_PATH = os.path.join(_THIS_MODULE_PATH, "templates")

_ENV = Environment(
    loader=FileSystemLoader(searchpath=_TEMPLATES_PATH),
    autoescape=select_autoescape(),
)


def generate_html(
    input_files: SarifFileSet, image_file: str, output: str, output_multiple_files: bool
):
    """
    Generate HTML file from the input files.
    """
    date_val = datetime.now()

    if image_file:
        image_mime_type = "image/" + os.path.splitext(image_file)[-1]
        if image_mime_type == "image/jpg":
            image_mime_type = "image/jpeg"
        with open(image_file, "rb") as input_file:
            image_data = input_file.read()

        image_data_base64 = base64.b64encode(image_data).decode("utf-8")
    else:
        image_mime_type = None
        image_data_base64 = None

    output_file = output
    if output_multiple_files:
        for input_file in input_files:
            output_file_name = input_file.get_file_name_without_extension() + ".html"
            print(
                "Writing HTML report for",
                input_file.get_file_name(),
                "to",
                output_file_name,
            )
            _generate_single_html(
                input_file,
                os.path.join(output, output_file_name),
                date_val,
                image_mime_type,
                image_data_base64,
            )
        output_file = os.path.join(output, "static_analysis_output.html")
    source_description = input_files.get_description()
    print(
        "Writing HTML report for",
        source_description,
        "to",
        os.path.basename(output_file),
    )
    _generate_single_html(
        input_files, output_file, date_val, image_mime_type, image_data_base64
    )


def _generate_single_html(
    input_file, output_file, date_val, image_mime_type, image_data_base64
):

    all_tools = input_file.get_distinct_tool_names()

    total_distinct_issue_codes = 0
    problems = []

    issues_by_severity = input_file.get_records_grouped_by_severity()
    for (severity, issues_of_severity) in issues_by_severity.items():
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

    chart_data = charts.generate_severity_pie_chart(input_file, output_file=None)
    if chart_data:
        chart_image_data_base64 = base64.b64encode(chart_data).decode("utf-8")
    else:
        chart_image_data_base64 = None

    filtered = None
    filter_stats = input_file.get_filter_stats()
    if filter_stats:
        filtered = f"Results were filtered by {filter_stats}."

    template = _ENV.get_template("sarif_summary.html")
    html_content = template.render(
        report_type=", ".join(all_tools),
        report_date=date_val,
        severities=", ".join(issues_by_severity.keys()),
        total=total_distinct_issue_codes,
        problems=problems,
        image_mime_type=image_mime_type,
        image_data_base64=image_data_base64,
        chart_image_data_base64=chart_image_data_base64,
        filtered=filtered,
    )

    with open(output_file, "wt", encoding="utf-8") as file_out:
        file_out.write(html_content)


def _enrich_details(histogram, records_of_severity):
    enriched_details = []

    for (error_code, count) in histogram:
        error_lines = [e for e in records_of_severity if e["Code"] == error_code]
        lines = sorted(
            error_lines, key=lambda x: x["Location"] + str(x["Line"]).zfill(6)
        )
        enriched_details.append({"code": error_code, "count": count, "details": lines})
    return enriched_details
