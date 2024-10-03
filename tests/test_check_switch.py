from sarif.cmdline.main import _check
from sarif import sarif_file

SARIF = {
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "Tool"
        }
      },
      "results": [
        {
          "level": "warning",
          "ruleId": "rule"
        }
      ]
    }
  ]
}


def test_check():
    fileSet = sarif_file.SarifFileSet()
    fileSet.add_file(sarif_file.SarifFile("SARIF", SARIF))

    result = _check(fileSet, "error")
    assert result == 0

    result = _check(fileSet, "warning")
    assert result == 1

    result = _check(fileSet, "note")
    assert result == 1
