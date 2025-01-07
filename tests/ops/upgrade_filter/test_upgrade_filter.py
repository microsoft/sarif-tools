import os
import tempfile

from sarif.operations import upgrade_filter_op

INPUT_FILTER = """
description: Test filter
#comment
+: include_with_prefix
include_without_prefix
-: exclude
"""


EXPECTED_OUTPUT_TXT = """configuration:
  check-line-number: true
  default-include: true
description: Test filter
exclude:
- author-mail: exclude
include:
- author-mail: include_with_prefix
- author-mail: include_without_prefix
"""


def test_upgrade_filter():
    with tempfile.TemporaryDirectory() as tmp:
        input_file_path = os.path.join(tmp, "input_filter.txt")
        with open(input_file_path, "wb") as f_in:
            f_in.write(INPUT_FILTER.encode())

        output_file_path = os.path.join(tmp, "output.txt")
        upgrade_filter_op.upgrade_filter_file(input_file_path, output_file_path)

        with open(output_file_path, "rb") as f_out:
            output = f_out.read().decode()

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep)
