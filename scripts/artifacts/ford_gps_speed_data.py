__artifacts_v2__ = {
    "GPS_Speed_Data": {
        "name": "GPS Speed Data",
        "description": "Scrapes the gps speed data from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-06",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/*fdplog.np.txt*'),
        "function": "get_ford_gps_speed_data"
    }
}

import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford']
platforms = ['']

## Get connected Bluetooth Devices
def get_ford_gps_speed_data(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r", encoding="cp437") as f:
            timestamp = speed = latitude = longitude = heading = compass_dir = '' # Initialize Variables
            for line in f:  # Search line for certain keywords
                timestamp = speed = latitude = longitude = heading = compass_dir = '' # Initialize Variables
                if line == "":
                    continue
                splits1 = ''
                splits2 = ''
                if "[fdp@30513 tid=\"7\"] DR data:" in line and "GPSDataValid=1" in line:
                    timestamp = speed = latitude = longitude = heading = compass_dir = '' # Initialize Variables
                    splits1 = line.split("[fdp@30513 tid=\"7\"] DR data:")[1].strip().strip("\n")
                    line = next(f)
                    while "[fdp@30513 tid=\"7\"]" not in line:
                        line = next(f)
                    splits2 = line.split("[fdp@30513 tid=\"7\"] ")[1].strip()
                    if splits2[0] == "S":
                        full_line = splits1 + " " +splits2
                    else:
                        full_line = splits1 + splits2

                    #print(full_line)
                    lineparts = full_line.split(" ")
                    timestamp = lineparts[4] + " " + lineparts[5]
                    heading = lineparts[9].split("Heading=")[1]
                    compass_dir = lineparts[12].split("compDir=")[1]
                    speed = lineparts[13].split("Speed=")[1] 
                if (timestamp, speed, heading, compass_dir) not in data_list and timestamp != '' and speed != "" and compass_dir != "" and heading != '':
                    data_list.append((timestamp, speed, heading, compass_dir)) # Add new found data to datalist
                                    
    if len(data_list) > 0: # Check to see if Data was found
        report = ArtifactHtmlReport('GPS Speed Data')
        report.start_artifact_report(report_folder, f'GPS Speed Data')
        report.add_script()
        data_headers = ('Time Stamp', "Speed", "Heading", "Compass Direction")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'GPS Speed Data'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No GPS Speed Data found')
