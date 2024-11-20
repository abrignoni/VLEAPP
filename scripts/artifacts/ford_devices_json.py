__artifacts_v2__ = {
    "Devices_from_json": {
        "name": "Devices from json",
        "description": "Scrapes the devices.json data from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-04",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/devices.json'),
        "function": "get_devices"
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
def get_devices(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            address = name = serial = '' # Initialize Variables
            for line in f:  # Search line for certain keywords
                if line == "":
                    continue
                splits1 = ''
                #NOT DONE CHANGE BELOW
                if "\"bluetooth_mac_address\": \"" in line and address != "":
                    if (address, serial, name) not in data_list and name != '' and address != "" and serial != "":
                        data_list.append((address, serial, name)) # Add new found data to datalist
                    name = serial = '' # Initialize Variables
                    splits1 = line.split("\"bluetooth_mac_address\": \"")
                    address = splits1[1].strip()[:-2]
                if "\"bluetooth_mac_address\": \"" in line and address == "":
                    splits1 = line.split("\"bluetooth_mac_address\": \"")
                    address = splits1[1].strip()[:-2]
                if "\"serial_number\": \"" in line:
                    splits1 = line.split("\"serial_number\": \"")
                    serial = splits1[1].strip()[:-2]
                if "\"device_name\": \"" in line:
                    splits1 = line.split("\"device_name\": \"")
                    name = splits1[1].strip()[:-2]
            if (address, serial, name) not in data_list and name != '' and address != "" and serial != "":
                data_list.append((address, serial, name)) # Add new found data to datalist
                                    
    if len(data_list) > 0: # Check to see if Data was found
        report = ArtifactHtmlReport('Devices in devices.json')
        report.start_artifact_report(report_folder, f'Devices in devices.json')
        report.add_script()
        data_headers = ('Mac_Address', 'Serial', "Name")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Devices in devices.json'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Devices in devices.json found')
