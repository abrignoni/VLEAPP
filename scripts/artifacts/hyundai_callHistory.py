import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_callHistory(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        with open(file_found, 'r') as f:
            pass
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Call History')
        report.start_artifact_report(report_folder, f'Call History')
        report.add_script()
        data_headers = ('ID','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Call History'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Call Histoyr found')


__artifacts__ = {
    "call history": (
        "call history",
        ('*/bluetooth.DB_BMS/CH_*.db'),
        get_callHistory),
}