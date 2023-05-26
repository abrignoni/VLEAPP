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
            for line in f:
                pass
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Bluetooth Devices')
        report.start_artifact_report(report_folder, f'Bluetooth Devices')
        report.add_script()
        # look for: 'name: ', 'bdAddr: ', 
        data_headers = ('Device Address','Device Friendly Name')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()

        tsvname = f'Vehicle Info'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Vehicle Info available')

## Get known contacts
def get_contacts(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            pass # Insert code here
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Vehicle Info')
        report.start_artifact_report(report_folder, f'Vehicle Info')
        report.add_script()
        data_headers = ('Key','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
    
        tsvname = f'Vehicle Info'
        tsv(report_folder, data_headers, data_list, tsvname)

    else:
        logfunc(f'No Vehicle Info available')

## Get recent calls
#def get_calllogs(files_found, report_folder, seeker, wrap_text):
#   print("nothing")

## Get GPS data

def timeorder(line):
    month = line.split('/', 3)[0]
    day = line.split('/', 3)[1]
    yeartime = line.split('/', 3)[2]
    year = yeartime.split(' ')[0]
    time = yeartime.split(' ')[1]
    timestamp = f'{year}-{month}-{day} {time}'
    return timestamp


def get_gpsdata(files_found, report_folder, seeker, wrap_text):
    data_list = []
    data_list_dev = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            for line in f:
                if 'GPS Positioning' in line: #put a print here to get all GPS stuff related to nav    
                    if 'dev_loc_results' in line:
                        if 'ERROR  RPT!!!' in line:
                            pass 
                        elif 'Longitude =' in line:
                            #print(line)
                            timestamp = timeorder(line)
                            devmatchObj1 = re.search(r"(Longitude =  ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj2 = re.search(r"(Latitude = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj7 = re.search(r"(Altitude = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj8 = re.search(r"(Heading = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            category = 'NAV_FRAMEWORK_IF'
                            subcategory = 'dev_loc_results'
                            #logfunc(line)
                            data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
                        elif 'Lon =' in line:
                            #print(line)
                            timestamp = timeorder(line)
                            devmatchObj1 = re.search(r"(Lon =  ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj2 = re.search(r"(Lat = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj7 = re.search(r"(Alt = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj8 = re.search(r"(Heading = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            category = 'NAV_FRAMEWORK_IF'
                            subcategory = 'dev_loc_results'
                            #logfunc(line)
                            data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
            if len(data_list) > 0:
                report = ArtifactHtmlReport('Vehicle Info')
                report.start_artifact_report(report_folder, f'Vehicle Info')
                report.add_script()
                data_headers = ('Key','Value')
                report.write_artifact_data_table(data_headers, data_list, file_found)
                report.end_artifact_report()
                
                tsvname = f'Vehicle Info'
                tsv(report_folder, data_headers, data_list, tsvname)
                
            else:
                logfunc(f'No Vehicle Info available')



__artifacts__ = {
    "bluetooth_devices": (
        "bluetooth devices",
        ('*/mnt/p3/betula/bt_log.txt'),
        get_btDevices),
    "contacts": (
        "contacts",
        ('*/mnt/p3/voice/asr/context/phonebook/*.txt'),
        get_contacts),
   # "call_logs": (
     #  "call_logs",
      #  ('*/com.android.cooldata/files/cool.xml'),
     #   get_calllogs),
    "gps_data": (
        "gps_data",
        ('*/mnt/p3/persistence/nonvol_*.ps'),
        get_gpsdata)

    
}