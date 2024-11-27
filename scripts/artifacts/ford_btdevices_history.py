__artifacts_v2__ = {
    "BT_Device_History": {
        "name": "BT Device History",
        "description": "Scrapes the BT Device History from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-10-14",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/*smartdevicelink.log'),
        "function": "get_bt_device_hist"
    }
}

import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford','F-150']
platforms = ['']

def get_time(line):
    desired_part = line.split("]")[0]
    date = desired_part.split("[")[1].split(" ")
    day = date[0]
    month = date[1]
    year = date[2]
    time = date[3][0:-4]
    #print(time)
    return f"{year}-{month}-{day} {time}"
    

## Get connected Bluetooth Devices
def get_bt_device_hist(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            time = name = serial = uuid = connection_type = incoming ='' # Initialize Variables
            for line in f:  # Search line for certain keywords
                if line == "":
                    continue
                splits1 = ''
                if "appeared: Device name: " in line:
                    time = get_time(line)
                    splits1 = line.split("appeared: Device name: ")
                    name = splits1[1].strip()
                    if splits1[0][-3:] == "dis":
                        incoming = "Device Disconnected"
                    else: 
                        incoming = "Device Connected"
                    line = next(f)
                    splits1 = line.split("Device serial: ")
                    serial = splits1[1].strip() 
                    line = next(f)
                    splits1 = line.split("Device uuid: ")
                    uuid = splits1[1].strip()
                    line = next(f)
                    splits1 = line.split("Device type: ")
                    connection_type = splits1[1].strip()
                # Add found item to data list                
                if (time, serial, name, uuid, connection_type, incoming) not in data_list and name != '' and time != "" and serial != "" and connection_type != "" and uuid != "" and incoming != "":
                    data_list.append((time, serial, name, uuid, connection_type, incoming)) # Add new found data to datalist
    
    if len(data_list) > 0: # Check to see if Data found
        report = ArtifactHtmlReport('BT Device History')
        report.start_artifact_report(report_folder, f'BT Device History')
        report.add_script()
        data_headers = ('Time', 'Serial', "Name", "uuid", "Connection Type", "Incoming/Outgoing")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'BT Device History'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No BT Device History found')

