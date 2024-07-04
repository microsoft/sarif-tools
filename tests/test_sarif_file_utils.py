from sarif import sarif_file_utils


def test_combine_code_and_description_short():
    cd = sarif_file_utils.combine_code_and_description(
        "ABC123", "Some short description"
    )
    assert cd == "ABC123 Some short description"
    assert len(cd) <= 120


def test_combine_code_and_description_long_desc():
    cd = sarif_file_utils.combine_code_and_description(
        "ABC123", " ".join(f"blah{i}" for i in range(1, 30))
    )
    assert (
        cd
        == "ABC123 blah1 blah2 blah3 blah4 blah5 blah6 blah7 blah8 blah9 blah10 blah11 blah12 blah13 blah14 blah15 blah16 ..."
    )
    assert len(cd) <= 120


def test_combine_code_and_description_long_code():
    long_code = "".join(f"A{i}" for i in range(1, 36)) + "BC"
    assert (
        len(long_code) == 98
    ), "98 is right length to hit 'placeholder too large for max width' without defensive code"
    cd = sarif_file_utils.combine_code_and_description(
        long_code, "wow that's a long code"
    )
    assert cd == f"{long_code} wow that's a ..."
    assert len(cd) <= 120
    long_code = "".join(f"A{i}" for i in range(1, 50))
    cd = sarif_file_utils.combine_code_and_description(
        long_code, "wow that's a long code"
    )
    assert cd == long_code
