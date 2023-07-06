import csv
import os
import sqlite3

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_callHistory(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        res = cursor.execute("SELECT name FROM sqlite_master WHERE name='bluetooth_callhistory'")
        all_rows = res.fetchall()
        usageentries = len(all_rows)
        if usageentries > 0:
            for row in all_rows:
                data_list = []
                data_list_as_is = []
                    
                tablename = (row[0])
                tablenamenum = tablename.split('_')[2]

                    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Call History')
        report.start_artifact_report(report_folder, f'Call History')
        report.add_script()
        data_headers = ('ID','given_name', 'family_name', 'phone_number', 'calltype', 'date', 'date_sort', 'duration', 'numberType')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Call History'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Call History found')


__artifacts__ = {
    "call history": (
        "call history",
        ('*/bluetooth/DB_BMS/CH_*.db'),
        get_callHistory),
}