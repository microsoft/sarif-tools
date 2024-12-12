import os
import tempfile

from sarif.operations import ls_op


def test_ls():
    file_names = ["file1.sarif", "file2.sarif", "aaaa.sarif"]

    with tempfile.TemporaryDirectory() as tmp:
        for file_name in file_names:
            with open(os.path.join(tmp, file_name), "wb") as f_in:
                f_in.write("{}".encode())

        output_path = os.path.join(tmp, "output.txt")
        ls_op.print_ls([tmp], output_path)

        with open(output_path, "rb") as f_out:
            output = f_out.read().decode().splitlines()

        assert len(output) == len(file_names) + 1
        assert output[0] == tmp + ":"
        assert output[1:] == sorted(["  " + file_name for file_name in file_names])
