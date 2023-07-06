import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_infotainmentData(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.contains("[") or line.contains("]"):
                    pass
                else:
                    splits = line.split("=")
                    data_list.append((splits[0], splits(1)))
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Infotainment Data')
        report.start_artifact_report(report_folder, f'Infotainment Data')
        report.add_script()
        data_headers = ('ID','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Infotainment Data'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Infotainment Data found')


__artifacts__ = {
    "Accessory Data Hyundai": (
        "Accessory Data Hyundai",
        ('*/wifi/settings'),
        get_infotainmentData),
}