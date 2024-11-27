__artifacts_v2__ = {
    "Ford_Model": {
        "name": "Vehicle Model",
        "description": "Scrapes the model info from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-04",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/bluetooth_v1.ddb'),
        "function": "get_Model"
    }
}
import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford','Bronco Raptor', 'F-150', 'F-250']
platforms = ['']

def get_Model(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r", encoding='cp437') as f:
            model = '' # Initialize Variable
            for line in f:  # Search line for certain keywords
                if line == "":
                    continue
                splits1 = ''
                splits2 = ''
                if "device_name" in line:
                    line = next(f)
                    splits1 = line.split("<Value>")
                    splits2 = splits1[1].split("<")
                    model = splits2[0].strip()
                    
                # Add found item to data list                
                if (model not in data_list) and model != '':
                    data_list.append(model) # Add new found data to datalist
    if len(data_list) > 0: # Check to see if data found
        for item in data_list:
            logdevinfo(f"Model from Bluetooth_v1.ddb: {item}")
    else:
        logfunc(f'No Vehicle Model found')
