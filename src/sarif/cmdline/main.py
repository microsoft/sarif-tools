"""
Program entry point for sarif-tools on the command line.
"""

import argparse
from importlib import metadata
import os
import sys

from sarif import loader, sarif_file

from sarif.operations import (
    blame_op,
    csv_op,
    diff_op,
    html_op,
    ls_op,
    summary_op,
    trend_op,
    word_op,
)


def main():
    """
    Entry point function.
    """
    args = ARG_PARSER.parse_args()

    if args.debug:
        print(f"SARIF tools v{_read_package_version()}")
        print(f"Running code from {__file__}")
        known_args_summary = ", ".join(
            f"{key}={getattr(args, key)}" for key in vars(args)
        )
        print(f"Known arguments: {known_args_summary}")

    exitcode = args.func(args)
    return exitcode


def _create_arg_parser():
    cmd_list = """commands:
  blame       Enhance SARIF file with information from `git blame`
  csv         Write a CSV file listing the issues from the SARIF files(s) specified
  diff        Find the difference between two [sets of] SARIF files
  html        Write a file with HTML representation of SARIF file
  ls          List all SARIF files in the directories specified
  summary     Write a text summary with the counts of issues from the SARIF files(s) specified
  trend       Write a CSV file with time series data from the SARIF file(s) specified, which must
              have timestamps in the filenames in format "yyyymmddThhmmssZ"
  usage       (Command optional) - print usage and exit
  word        Produce MS Word .docx summaries of the SARIF files specified
Run `sarif <COMMAND> --help` for command-specific help.
"""
    package_version = _read_package_version()
    parser = argparse.ArgumentParser(
        prog="sarif",
        description="Process sets of SARIF files",
        epilog=cmd_list,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(func=_usage)
    subparsers = parser.add_subparsers(dest="command", help="command")
    subparser = {}
    for (cmd, function) in _COMMANDS.items():
        subparser[cmd] = subparsers.add_parser(cmd)
        subparser[cmd].set_defaults(func=function)

    # Common options
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"sarif-tools version {package_version}",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print information useful for debugging"
    )
    parser.add_argument(
        "--check",
        "-x",
        type=str,
        choices=sarif_file.SARIF_SEVERITIES,
        help="Exit with error code if there are any issues of the specified level "
        + "(or for diff, an increase in issues at that level).",
    )

    for cmd in ["blame", "csv", "html", "summary", "word"]:
        subparser[cmd].add_argument(
            "--output", "-o", type=str, help="Output file or directory"
        )
    for cmd in ["diff", "ls", "trend", "usage"]:
        subparser[cmd].add_argument("--output", "-o", type=str, help="Output file")

    for cmd in ["csv", "diff", "summary", "html", "trend", "word"]:
        subparser[cmd].add_argument(
            "--blame-filter-include",
            "-i",
            type=str,
            help="File containing a newline-separated filter list of author-mail to include",
        )
        subparser[cmd].add_argument(
            "--blame-filter-exclude",
            "-x",
            type=str,
            help="File containing a newline-separated filter list of author-mail to exclude",
        )

    # Command-specific options
    subparser["blame"].add_argument(
        "--code",
        "-c",
        metavar="PATH",
        type=str,
        help="Path to git repository; if not specified, the current working directory is used",
    )
    # csv defaults to no trimming
    subparser["csv"].add_argument(
        "--autotrim",
        "-a",
        action="store_true",
        help="Strip off the common prefix of paths in the CSV output",
    )
    # word and html default to trimming
    for cmd in ["html", "word"]:
        subparser[cmd].add_argument(
            "--no-autotrim",
            "-n",
            action="store_true",
            help="Do not strip off the common prefix of paths in the CSV output",
        )
        subparser[cmd].add_argument(
            "--image",
            "-i",
            type=str,
            help="Image to include at top of file - SARIF logo by default",
        )
    # csv, html and word allow trimmable paths to be specified
    for cmd in ["csv", "word", "html"]:
        subparser[cmd].add_argument(
            "--trim",
            metavar="PREFIX",
            action="append",
            type=str,
            help="Prefix to strip from issue paths, e.g. the checkout directory on the build agent",
        )
    # Most commands take an arbitrary list of SARIF files or directories
    for cmd in _COMMANDS:
        if cmd not in ["diff", "usage"]:
            subparser[cmd].add_argument(
                "files_or_dirs",
                metavar="file_or_dir",
                type=str,
                nargs="*",
                help="A SARIF file or a directory containing SARIF files",
            )
    subparser["diff"].add_argument(
        "old_file_or_dir",
        type=str,
        nargs=1,
        help="An old SARIF file or a directory containing the old SARIF files",
    )
    subparser["diff"].add_argument(
        "new_file_or_dir",
        type=str,
        nargs=1,
        help="A new SARIF file or a directory containing the new SARIF files",
    )

    subparser["trend"].add_argument(
        "--dateformat",
        "-f",
        type=str,
        choices=["dmy", "mdy", "ymd"],
        default="dmy",
        help="Date component order to use in output CSV.  Default is `dmy`",
    )
    return parser


def _read_package_version():
    try:
        return metadata.version("sarif-tools")
    except metadata.PackageNotFoundError:
        return "local"


def _check(input_files: sarif_file.SarifFileSet, check_level):
    ret = 0
    if check_level:
        counts = input_files.get_result_count_by_severity()
        for severity in sarif_file.SARIF_SEVERITIES:
            ret += counts.get(severity, 0)
            if severity == check_level:
                break
    if ret > 0:
        sys.stderr.write(
            f"Check: exiting with return code {ret} due to issues at or above {check_level} severity\n"
        )
    return ret


def _load_blame_filter_file(file_path):
    regexes = []
    substrings = []
    with open(file_path) as file_in:
        for l in file_in.readlines():
            lstrip = l.strip()
            if lstrip:
                if lstrip.startswith("/") and lstrip.endswith("/") and len(lstrip) > 2:
                    regexes.append(lstrip[1 : len(lstrip) - 1])
                else:
                    substrings.append(lstrip)
    return (substrings, regexes)


def _init_blame_filtering(input_files, args):
    if args.blame_filter_include or args.blame_filter_exclude:
        (include_substrings, include_regexes) = (
            _load_blame_filter_file(args.blame_filter_include)
            if args.blame_filter_include
            else ([], [])
        )
        (exclude_substrings, exclude_regexes) = (
            _load_blame_filter_file(args.blame_filter_exclude)
            if args.blame_filter_exclude
            else ([], [])
        )
        input_files.init_blame_filter(
            include_substrings, include_regexes, exclude_substrings, exclude_regexes
        )


def _init_path_prefix_stripping(input_files, args, strip_by_default):
    if strip_by_default:
        autotrim = not args.no_autotrim
    else:
        autotrim = args.autotrim
    trim_paths = args.trim
    if autotrim or trim_paths:
        input_files.init_path_prefix_stripping(autotrim, trim_paths)


def _ensure_dir(dir_path):
    """
    Create directory if it does not exist
    """
    if dir_path and not os.path.isdir(dir_path):
        os.makedirs(dir_path)


def _prepare_output(
    input_files: sarif_file.SarifFileSet, output_arg, output_file_extension: str
):
    """
    Returns (output, output_multiple_files)
    output is args.output, or if that wasn't specified, a default output file based on the inputs
    and the file extension.
    output_multiple_files determines whether to output one file per input plus a totals file.
    It is false if there is only one input file, or args.output is a file that exists,
    or args.output ends with the expected file extension.
    """
    input_file_count = len(input_files)
    if input_file_count == 0:
        return ("static_analysis_output" + output_file_extension, False)
    if input_file_count == 1:
        derived_output_filename = (
            input_files[0].get_file_name_without_extension() + output_file_extension
        )
        if output_arg:
            if os.path.isdir(output_arg):
                return (os.path.join(output_arg, derived_output_filename), False)
            _ensure_dir(os.path.dirname(output_arg))
            return (output_arg, False)
        return (derived_output_filename, False)
    # Multiple input files
    if output_arg:
        if os.path.isfile(output_arg) or output_arg.strip().upper().endswith(
            output_file_extension.upper()
        ):
            # Output single file, even though there are multiple input files.
            _ensure_dir(os.path.dirname(output_arg))
            return (output_arg, False)
        _ensure_dir(output_arg)
        return (output_arg, True)
    return (os.getcwd(), True)


####################################### Command handlers #######################################


def _blame(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    (output, multiple_file_output) = _prepare_output(input_files, args.output, ".sarif")
    blame_op.enhance_with_blame(
        input_files, args.code or os.getcwd(), output, multiple_file_output
    )
    return _check(input_files, args.check)


def _csv(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    input_files.init_default_line_number_1()
    _init_path_prefix_stripping(input_files, args, strip_by_default=False)
    _init_blame_filtering(input_files, args)
    (output, multiple_file_output) = _prepare_output(input_files, args.output, ".csv")
    csv_op.generate_csv(input_files, output, multiple_file_output)
    return _check(input_files, args.check)


def _diff(args):
    original_sarif = loader.load_sarif_files(args.old_file_or_dir[0])
    new_sarif = loader.load_sarif_files(args.new_file_or_dir[0])
    _init_blame_filtering(original_sarif, args)
    _init_blame_filtering(new_sarif, args)
    return diff_op.print_diff(original_sarif, new_sarif, args.output, args.check)


def _html(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    input_files.init_default_line_number_1()
    _init_path_prefix_stripping(input_files, args, strip_by_default=True)
    _init_blame_filtering(input_files, args)
    (output, multiple_file_output) = _prepare_output(input_files, args.output, ".html")
    html_op.generate_html(input_files, args.image, output, multiple_file_output)
    return _check(input_files, args.check)


def _ls(args):
    ls_op.print_ls(args.files_or_dirs, args.output)
    if args.check:
        input_files = loader.load_sarif_files(*args.files_or_dirs)
        return _check(input_files, args.check)
    return 0


def _summary(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    _init_blame_filtering(input_files, args)
    (output, multiple_file_output) = (None, False)
    if args.output:
        (output, multiple_file_output) = _prepare_output(
            input_files, args.output, ".txt"
        )
    summary_op.generate_summary(input_files, output, multiple_file_output)
    return _check(input_files, args.check)


def _trend(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    input_files.init_default_line_number_1()
    _init_blame_filtering(input_files, args)
    if args.output:
        _ensure_dir(os.path.dirname(args.output))
        output = args.output
    else:
        output = "static_analysis_trend.csv"
    trend_op.generate_trend_csv(input_files, output, args.dateformat)
    return _check(input_files, args.check)


def _usage(args):
    if hasattr(args, "output") and args.output:
        with open(args.output, "w", encoding="utf-8") as file_out:
            ARG_PARSER.print_help(file_out)
        print("Wrote usage instructions to", args.output)
    else:
        ARG_PARSER.print_help()
    if args.check:
        sys.stderr.write("Spurious --check argument")
        return 1
    return 0


def _word(args):
    input_files = loader.load_sarif_files(*args.files_or_dirs)
    input_files.init_default_line_number_1()
    _init_path_prefix_stripping(input_files, args, strip_by_default=True)
    _init_blame_filtering(input_files, args)
    (output, multiple_file_output) = _prepare_output(input_files, args.output, ".docx")
    word_op.generate_word_docs_from_sarif_inputs(
        input_files, args.image, output, multiple_file_output
    )
    return _check(input_files, args.check)


_COMMANDS = {
    "blame": _blame,
    "csv": _csv,
    "diff": _diff,
    "html": _html,
    "ls": _ls,
    "summary": _summary,
    "trend": _trend,
    "usage": _usage,
    "word": _word,
}

ARG_PARSER = _create_arg_parser()
