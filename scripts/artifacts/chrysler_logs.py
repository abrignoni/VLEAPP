__artifacts_v2__ = {
    "Location_logs": {
        "name": "Location Logs",
        "description": "Scrapes the log data from Chrysler Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-10-07",  # Date of the latest version
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/persistentLogs/*/Log*'),
        "function": "get_location_logs"
    }
}

import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Grand Cherokee']
platforms = ['']

def get_location_logs(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r", encoding='cp437') as f:
            date = time = latitude = longitude = zip_code = speed = altitude = course = h_acc = v_acc = azimuth = method = '' # Initialize Variables
            for line in f:  # Search line for certain keywords
                if line == "":
                    continue
                splits1 = ''
                splits2 = ''
                if "JSR179InterfaceImpl [INFO] " in line:
                    splits1 = line.split(" ")
                    date = splits1[0].strip()
                    time = splits1[1].strip()[0:-4]
                    splits2 = line.split(" ")
                    method = "N/A" if splits2[-2] == ";" else splits2[-2][0:-1]  # Grab index we need but also remove trailing semicolon
                    azimuth = splits2[-5][0:-1]
                    speed = splits2[-7][0:-1]
                    course = splits2[-9][0:-1]
                    v_acc = splits2[-14][0:-1]
                    h_acc = splits2[-17][0:-1]
                    altitude = splits2[-20][0:-1]
                    zip_code = "Not found" if splits2[-22] == ";" else splits2[-22][0:-1] 
                    longitude = splits2[-25][0:-1]
                    latitude = splits2[-27][0:-1]
                    
                # Add found item to data list                
                if (date, time, latitude, longitude, zip_code, altitude, h_acc, v_acc, course, speed, azimuth, method) not in data_list and date != '' and time != "" and latitude != "" and longitude != "":
                    data_list.append((date, time, latitude, longitude, zip_code, altitude, h_acc, v_acc, course, speed, azimuth, method)) # Add new found data to datalist
    
    if len(data_list) > 0: # Check to see if Data found
        report = ArtifactHtmlReport('Location Logs')
        report.start_artifact_report(report_folder, f'Location Logs')
        report.add_script()
        data_headers = ('Date', 'Time', "Latitude", "Longitude", "Zip Code", "Altitude", "Horizontal Accuracy", "Vertical Accuracy", "Course", "Speed", "Azimuth", "Location Method")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Location Logs'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Location Logs found')

