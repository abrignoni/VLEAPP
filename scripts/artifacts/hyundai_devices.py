import csv
import os
import re

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_devices(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        devAddr = []
        devFriendlyName = []
        with open(file_found, 'r') as f:
            for line in f:
                line_str = str(line)
                line_str_2 = line_str # Copy of line 

                #Pattern to find addresses
                addrPattern = re.compile(r"[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+", re.IGNORECASE)

                #Given pattern, remove from copy of line to find only text
                line_str_2 = re.sub(addrPattern, '~~~', line_str_2)
                devFriendlyName_temp = line_str_2.split('~~~')
                if len(devFriendlyName_temp) == 1: # don't add garbage values to name list
                    logfunc("bytes(name): " + str(devFriendlyName_temp))
                    devFriendlyName_temp[0] = str(devFriendlyName_temp[0]).strip().strip('\x00').strip('\x01').strip('\x02')
                    if devFriendlyName_temp[0] not in devFriendlyName:
                        devFriendlyName.append(devFriendlyName_temp[0]) # add to name list
                        #logfunc("devFriendlyName_temp: " + devFriendlyName_temp[0])

                #Get addresses from pattern in given line
                result = re.findall(addrPattern, line_str)
                if len(result) == 1:
                    if result[0] not in devAddr:
                        devAddr.append(result[0])
                        #logfunc("Address result: " + str(result[0]))

                data_list = tuple(zip(devAddr, devFriendlyName))

    if len(data_list) > 0:
        report = ArtifactHtmlReport('Bluetooth Devices')
        report.start_artifact_report(report_folder, f'Bluetooth Devices')
        report.add_script()
        data_headers = ('Bluetooth MAC Address','Device Friendly Name')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Bluetooth Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Bluetooth Devices found')

__artifacts__ = {
    "connected devices": (
        "connected devices",
        ('*/wireless_dev_list.dat'),
        get_devices),
}