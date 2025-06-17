__artifacts_v2__ = {
    "geolocation_data": {
        "name": "Geolocation data",
        "description": "Scrapes the geolocation data from ford vehicles",
        "author": "@K7NGhost",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-6-16",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/*fdplog.np.txt*'),
        "function": "get_geolocation_data"
    }
}

import datetime
import re
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

def get_geolocation_data(files_found, report_folder, seeker, wrap_text, time_offset):
        timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)')
        coord_pattern = re.compile(r"lat=([-\d.]+),\s*lon=([-\d.]+),\s*alt=([-\d.]+)")
        trimble_output = []
        
        for file_path in files_found:
            with open(file_path, "r", encoding="cp437") as file:
                for line in file:
                    if "Trimble Output" in line:
                        timestamp_match = timestamp_pattern.search(line)
                        match = coord_pattern.search(line)
                        if match and timestamp_match:
                            timestamp = timestamp_match.group(1)
                            dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            lat, lon, alt = map(float, match.groups())
                            trimble_output.append((dt, lat, lon, alt))

        if len(trimble_output) > 0:
            report = ArtifactHtmlReport('geolocation data')
            report.start_artifact_report(report_folder, 'geolocation data')
            report.add_script()
            data_headers = ("Timestamp", "Latitude", "Longitude", "Altitude")
            report.write_artifact_data_table(data_headers, trimble_output, file_path)
            report.end_artifact_report()
            tsvname = f'geolocation data'
            tsv(report_folder, data_headers, trimble_output, tsvname)
        else:
            logfunc(f'no geolocation found')
                            