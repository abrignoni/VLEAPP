import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']



## Get Accessory data
def get_accessorydata(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
            with open(file_found, "r") as f:
                while(data_list == ''):
                        for line in f:
                            names = line.split("::")
                            data_list.append((names[0],names[1]))
                            logfunc(data_list)
                            #[A-Za-z]+::[A-Za-z]+   -  regex for the accessory_data.txt file

    if len(data_list) > 0:
        report = ArtifactHtmlReport('Accessory Data')
        report.start_artifact_report(report_folder, f'Accessory Data')
        report.add_script()
        data_headers = ('Name','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'Accessory Data'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Accessory Data Found')



        


__artifacts__ = {
       "accessory_data": (
         "accessory_data",
         ('*/media/accessory_data.txt'),
         get_accessorydata)
}