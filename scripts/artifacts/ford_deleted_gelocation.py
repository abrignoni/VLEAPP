__artifacts_v2__ = {
    "deleted_geolocation_data": {
        "name": "Deleted Geolocation data",
        "description": "Scrapes the geolocation data from deleted files from ford vehicles",
        "author": "@K7NGhost",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-6-17",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/deleted_*'),
        "function": "get_deleted_geolocation_data"
    }
}

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows
import re
import os

def get_deleted_geolocation_data(files_found, report_folder, seeker, wrap_text, time_offset):
    pattern = r'"altitude"\s*:\s*(-?[\d.]+)\s*,\s*"heading_angle"\s*:\s*(-?[\d.]+)\s*,\s*"lat"\s*:\s*(-?[\d.]+)\s*,\s*"lon"\s*:\s*(-?[\d.]+)\s*,\s*"speed"\s*:\s*(-?[\d.]+)\s*,\s*"timestamp"\s*:\s*(-?[\d.]+)'
    geolocation_data = []
    point_data = []
    for file in files_found:
        try:
            if os.path.isfile(file):
                with open(file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        matches = re.findall(pattern, line)
                        for altitude, heading_angle, lat, lon, speed, timestamp in matches:
                            #print(float(altitude), float(heading_angle), float(lat), float(lon), float(speed), float(timestamp))
                            geolocation_data.append((altitude, heading_angle, lat, lon, speed, timestamp))
        except Exception as e:
            print(e)
    print(geolocation_data)
    if len(geolocation_data) > 0:
        report = ArtifactHtmlReport('deleted geolocation data')
        report.start_artifact_report(report_folder, 'deleted geolocation data')
        report.add_script()
        data_headers = ("Altitude", "Heading_Angle", "Latitude", "Longitude", "Speed", "Timestamp")
        report.write_artifact_data_table(data_headers, geolocation_data, file)
        report.end_artifact_report()
        tsvname = f'deleted geolocation data'
        tsv(report_folder, data_headers, geolocation_data, tsvname)
    else:
        logfunc(f'no deleted geolocation found')