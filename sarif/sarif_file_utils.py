"""
Reusable utility functions for handling the SARIF format.

Primarily interrogating the `result` JSON defined at
https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/sarif-v2.1.0-cs01.html#_Toc16012594
"""

from typing import Tuple


def read_result_location(result) -> Tuple[str, str]:
    """
    Extract the file path and line number strings from the Result.

    Tools store this in different ways, so this function tries a few different JSON locations.
    """
    file_path = None
    line_number = None
    locations = result.get("locations", [])
    if locations and isinstance(locations, list):
        location = locations[0]
        physical_location = location.get("physicalLocation", {})
        # SpotBugs has some errors with no line number so deal with them by just leaving it at 1
        line_number = physical_location.get("region", {}).get("startLine", None)
        # For file name, first try the location written by DevSkim
        file_path = (
            location.get("physicalLocation", {})
            .get("address", {})
            .get("fullyQualifiedName", None)
        )
        if not file_path:
            # Next try the physical location written by MobSF and by SpotBugs (for some errors)
            file_path = (
                location.get("physicalLocation", {})
                .get("artifactLocation", {})
                .get("uri", None)
            )
        if not file_path:
            logical_locations = location.get("logicalLocations", None)
            if logical_locations:
                # Finally, try the logical location written by SpotBugs for some errors
                file_path = logical_locations[0].get("fullyQualifiedName", None)
    return (file_path, line_number)
