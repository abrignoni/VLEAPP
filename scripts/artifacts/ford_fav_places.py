__artifacts_v2__ = {
    "Favorite_Places": {
        "name": "Favorite places",
        "description": "Scrapes the the Places Storage data from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-06",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/recents_storage', '*/favorites_storage'),
        "function": "get_fav_places"
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
def get_fav_places(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r", encoding='cp437') as f:
            address = label = latitude = longitude = id = '' # Initialize Variables
            for line in f:  # Search line for certain keywords
                if line == "":
                    continue
                splits1 = ''
                splits2 = ''
                if "places {" in line and id != "":
                    label = "None" if label == "" else label
                    address = "None" if address == "" else address
                    if (id, label, address, latitude, longitude) not in data_list and id != '' and latitude != "" and longitude != "":
                        data_list.append((id, label, address, latitude, longitude)) # Add new found data to datalist
                        address = label = latitude = longitude = id = '' 
                if "id: " in line:
                    splits1 = line.split("id: \"")
                    id = splits1[1].strip()[:-1]
                if "label:" in line:
                    splits1 = line.split("label: \"")
                    label = splits1[1].strip()[:-1]
                if "lat: " in line:
                    splits1 = line.split("lat: ")
                    latitude = splits1[1].strip()
                if "lon: " in line:
                    splits1 = line.split("lon: ")
                    longitude = splits1[1].strip()
                if "formatted_address: \"" in line:
                    splits1 = line.split("formatted_address: \"")
                    address = splits1[1].strip()[:-1]
            label = "None" if label == "" else label
            address = "None" if address == "" else address
            if (id, label, address, latitude, longitude) not in data_list and id != '' and latitude != "" and longitude != "":
                data_list.append((id, label, address, latitude, longitude)) # Add new found data to datalist
                address = label = latitude = longitude = id = ''
                                    
    if len(data_list) > 0: # Check to see if Data was found
        report = ArtifactHtmlReport('Favorite Places')
        report.start_artifact_report(report_folder, f'Favorite Places')
        report.add_script()
        data_headers = ('ID', 'Label', "Address", "Latitude", "Longitude")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Favorite Places'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Favorite Places found')
