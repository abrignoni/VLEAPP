__artifacts_v2__ = {
    "Vin_Number": {
        "name": "Vin Numnber",
        "description": "Scrape the vin info from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-04",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/vin.txt'),
        "function": "get_info"
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
def get_info(files_found, report_folder, seeker, wrap_text, time_offset):
    vinlist = []
    data_list = []
    model = []
    for file_found in files_found:
        with open(file_found, "r", encoding="cp437") as f:
            vin = model = ''
            for line in f:
                found_num = False
                if line == "":
                    continue
                vinlist.append(line.strip())

    if len(vinlist) > 0: # Check to see if data found
        for item in vinlist:
            logdevinfo(f"VIN from Vin.txt: {item}")
    else:
        logfunc(f'No Vin Number found')

