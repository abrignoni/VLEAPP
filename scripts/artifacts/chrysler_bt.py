import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']

## Get connected Bluetooth Devices
def get_btDevices(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            devAddr = devFriendlyName = '' # Look for device addresses (hex) & friendly names
            for line in f:  # Search line for certain keywords
                splits1 = ''
                splits2 = ''
                if 'bdAddr: ' in line:
                    splits1 = line.split('bdAddr: ')
                    line = next(f)
                    line = next(f)
                    if 'name: ' in line:
                        splits2 = line.split('name: ')
                        devAddr = splits1[1]
                        devFriendlyName = splits2[1]
                    else: 
                        devAddr = devFriendlyName = ''
                # Add found item pair to data list                
                if (devAddr, devFriendlyName) not in data_list and devAddr != '':
                    data_list.append((devAddr, devFriendlyName)) # Add new found data to datalist
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Bluetooth Devices')
        report.start_artifact_report(report_folder, f'Bluetooth Devices')
        report.add_script()
        data_headers = ('Device Address','Device Friendly Name')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Bluetooth Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Bluetooth Devices found')



__artifacts__ = {
    "bluetooth_devices": (
        "bluetooth devices",
        ('*/mnt/p3/betula/bt_log.txt'),
        get_btDevices),
}
