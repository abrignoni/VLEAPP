import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, logfunc, tsv, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Alfa Romeo','Giulia']
platforms = []

def get_btSyncInfo(files_found, report_folder, seeker, wrap_text):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('agenda.sqlite'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    Select
    BT_DEVICE.LAST_SYNC,
    BT_DEVICE.BD_ADDRESS
    From BT_Device
    order by BT_DEVICE.LAST_SYNC ASC
    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []  
    
    if usageentries > 0:
        for row in all_rows:
            data_list.append((row[0], row[1]))

        description = 'Bluetooth Last Sync'
        report = ArtifactHtmlReport('Bluetooth Last Sync')
        report.start_artifact_report(report_folder, 'BT Last Sync', description)
        report.add_script()
        data_headers = ('Last Sync Date', 'BT Address')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = 'BT_LastSync'
        tsv(report_folder, data_headers, data_list, tsvname)
        
        tlactivity = 'BT_LastSync'
        timeline(report_folder, tlactivity, data_list, data_headers)
    else:
        logfunc('No bluetooth sync data available')
    


__artifacts__ = {
        "Alfa Romeo Bluetooth": (
                "Alfa Romeo Bluetooth",
                ('*/agenda.sqlite*'),
                get_btSyncInfo)
}
        
        
