import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']

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


__artifacts__ = {
        "diagnostic_data": (
        "diagnostic_data",
        ('*/persistence/nonvol_*.ps'),
        get_diagnosticdata)
}