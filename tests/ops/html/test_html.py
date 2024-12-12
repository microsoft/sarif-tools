import datetime
import os
import tempfile

from sarif.operations import html_op
from sarif import sarif_file

INPUT_SARIF = {
    "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "unit test"}},
            "results": [
                {
                    "ruleId": "CA2101",
                    "level": "error",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "file:///C:/Code/main.c",
                                    "index": 0,
                                },
                                "region": {"startLine": 24, "startColumn": 9},
                            }
                        }
                    ],
                }
            ],
        }
    ],
}


EXPECTED_OUTPUT_TXT = """<head>
    <style>
        #pageContainer {
            margin: auto;
            max-width: 1200px;
        }

        #heroContentGrid {
            align-content: center;
            display: grid;
            flex-grow: 1;
            grid-gap: 15px;
            grid-template-columns: auto auto;
            grid-template-rows: auto auto;
        }

        #heroContentGrid > div {
            align-self: center;
        }

        #hero: {
            align-items: center;
            display: flex;
        }

        #heroLogo {
            grid-column: 1;
            grid-row: 1;
            text-align: right;
        }

        #heroTitle {
            font-family: 'Roboto', sans-serif;
            font-size: 50px;
            grid-column: 2;
            grid-row: 1;
            line-height: 59px;
            text-align: left;
        }

        .collapsible {
          background-color: white;
          cursor: pointer;
          width: 100%;
          border: none;
          text-align: left;
          outline: none;
          font-size: 15px;
        }

        .active, .collapsible:hover {
          color: white;
          background-color: #555;
        }

        .collapsible:after {
          content: '\\002B';
          color: white;
          font-weight: bold;
          float: right;
          margin-left: 5px;
        }

        .active:after {
          content: "\\2212";
        }

        .content {
          padding: 0 18px;
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.2s ease-out;
          background-color: #f1f1f1;
        }
    </style>
</head>



<h3>Sarif Summary: <b>unit test</b></h3>
<h4>Document generated on: <b><date_val></b></h4>
<h4>Total number of distinct issues of all severities (error, warning, note): <b>1</b></h4>





<h3>Severity : error [ 1 ]</h3>
<ul>
    <li>
        <button class="collapsible">CA2101: <b>1</b></button>
        <div class="content">
            <ul>
                    <li>file:///C:/Code/main.c:24</li>
            </ul>
        </div>
    </li>
    
</ul>

<h3>Severity : warning [ 0 ]</h3>
<ul>
    
</ul>

<h3>Severity : note [ 0 ]</h3>
<ul>
    
</ul>
<script>
    var coll = document.getElementsByClassName("collapsible");
    var i;

    for (i = 0; i < coll.length; i++) {
      coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.maxHeight){
          content.style.maxHeight = null;
        } else {
          content.style.maxHeight = content.scrollHeight + "px";
        }
      });
    }
</script>"""


def test_html():
    mtime = datetime.datetime.now()
    input_sarif_file = sarif_file.SarifFile("INPUT_SARIF", INPUT_SARIF, mtime=mtime)

    input_sarif_file_set = sarif_file.SarifFileSet()
    input_sarif_file_set.files.append(input_sarif_file)

    with tempfile.TemporaryDirectory() as tmp:
        file_path = os.path.join(tmp, "output.csv")
        html_op.generate_html(
            input_sarif_file_set,
            None,
            file_path,
            output_multiple_files=False,
            date_val=mtime,
        )

        with open(file_path, "rb") as f_in:
            output = f_in.read().decode()

        # Remove pie chart before diffing
        pie_chart_start = output.find("<img")
        pie_chart_end = output.find("/>", pie_chart_start) + 2
        output = output[:pie_chart_start] + output[pie_chart_end:]

        assert output == EXPECTED_OUTPUT_TXT.replace("\n", os.linesep).replace(
            "<date_val>", mtime.strftime("%Y-%m-%d %H:%M:%S.%f")
        )
