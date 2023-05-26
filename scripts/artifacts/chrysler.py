import csv
import os

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
            for line in f:
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

## Get known contacts
def get_contacts(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
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
def get_gpsdata(files_found, report_folder, seeker, wrap_text):
    data_list = []




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