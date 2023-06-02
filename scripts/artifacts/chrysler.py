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

## Get known contacts
def get_contacts(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            pass

            
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
        logfunc(f'No Contacts')

## Get diagnostic data from Extraction
def get_diagnosticdata(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            id = ''
            val = ''
            count = 0
            for line in f:
                splits = ''
                #Search for key values in the diagnostic logs
                if count%2==0:
                    id = line
                else:
                    val = line
                    if (id not in data_list):
                        data_list.append((id, val))  
                count += 1           
    if len(data_list) > 0:
        #Send new data to report generator
        report = ArtifactHtmlReport('Diagnostic Data')
        report.start_artifact_report(report_folder, f'Diagnostic Data')
        report.add_script()
        data_headers = ('Key','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
    
        tsvname = f'Vehicle Info'
        tsv(report_folder, data_headers, data_list, tsvname)

    else:
        logfunc(f'No Diagnostic Data')

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
    #basename = os.path.basename(files_found)
    for file_found in files_found:
        with open(file_found, "r") as f:
            for line in f:
                line_str = str(line)
                line_str_decoded = bytes(line_str, "utf-8").decode("unicode_escape")
                line_decoded = re.sub('r\\\\x[0-9a-fA-F]{2}', "", line_str_decoded)
                line_wanted = line_decoded.encode('ascii', 'ignore').decode('ascii')
                timestamp = timeorder(line_wanted)
                devmatchObj1 = re.search(r"(Latitude\sread from\sPS: \d\d\.\d\d\d\d\d\d\sLongitude\sread\sfrom\sPS:\s-\d\d\.\d\d\d\d\d\d\d)", line_wanted)
               #devmatchObj2 = re.search(r"(Latitude ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                #devmatchObj7 = re.search(r"(Altitude = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                #devmatchObj8 = re.search(r"(Heading = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                category = 'NAV_FRAMEWORK_IF'
                subcategory = 'dev_loc_results'
                #data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
                data_list.append((timestamp,devmatchObj1[2], category, subcategory))
    if len(data_list) > 0:
        report = ArtifactHtmlReport('GPS Info')
        report.start_artifact_report(report_folder, f'GPS Info')
        report.add_script()
        data_headers = ('Key','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'Vehicle Info'
        tsv(report_folder, data_headers, data_list, tsvname)
        
    else:
        logfunc(f'No GPS Info Found')



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
         ('*/mnt/p3/log/slogs2'),
         get_gpsdata),
    "diagnostic_data": (
        "diagnostic_data",
        ('*/mnt/p3/persistence/nonvol_*.ps'),
        get_diagnosticdata)

    
}
