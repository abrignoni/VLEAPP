import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford Mustang','F-150']
platforms = ['SYNC3.2V2','SYNCGen3.0_3.0.18093_PRODUCT','SyncGen3_v2_b', 'SYNCGen3.0_1.0.15139_PRODUCT']

def get_vehicleInfo(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            for line in f:
                splits = line.split('::')
                totalvalues = len(splits)
                if totalvalues > 1:
                    key = splits[0].strip()
                    value = splits[1].strip()
                    if 'DE0' not in splits[0]:
                        data_list.append((key, value))
                        
                        if  key == 'fuellevel' :
                            logdevinfo(f"Fuel Level: {value}")
                        if  key == 'ignitionstate' :
                            logdevinfo(f"Ignition State: {value}")
                        if  key == 'navigation' :
                            logdevinfo(f"Navigation: {value}")
                        if  key == 'odometer' :
                            logdevinfo(f"Odometer: {value}")
                        if  key == 'platform' :
                            logdevinfo(f"Platform: {value}")
                        if  key == 'vin' :
                            logdevinfo(f"VIN from PPSP: {value}")
                        if  key == 'vmcufpn' :
                            logdevinfo(f"Firmware: {value}")
            
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
        "Vehicle Info": (
                "Vehicle Info",
                ('*/ppsp/services/reconn/vehicle'),
                get_vehicleInfo)
}