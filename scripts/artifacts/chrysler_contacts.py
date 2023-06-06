import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']



## Get known contacts
def get_contacts(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            name = ''
            information = ''
            count = 0
            for line in f:
                splits = ''
                #Search for key values in the diagnostic logs
                if count%2==0:
                    name = line
                else:
                    information = line
                    if (name not in data_list):
                        data_list.append((name, information))  
                count += 1   
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Contacts List')
        report.start_artifact_report(report_folder, f'Contacts List')
        report.add_script()
        data_headers = ('Name','Information')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
    
        tsvname = f'Contacts List'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Contacts')


        __artifacts__ = {
       "contacts": (
        "contacts",
        ('*/mnt/p3/voice/asr/context/phonebook/*.txt'),
        get_contacts)
}