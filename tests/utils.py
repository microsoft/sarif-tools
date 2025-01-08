import json
import os


def get_sarif_schema():
    # JSON Schema file for SARIF obtained from https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/schemas/
    sarif_schema_file = os.path.join(
        os.path.dirname(__file__), "sarif-schema-2.1.0.json"
    )
    with open(sarif_schema_file, "rb") as f_schema:
        return json.load(f_schema)
