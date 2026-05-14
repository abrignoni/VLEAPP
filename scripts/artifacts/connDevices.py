import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, tsv, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Chevrolet','Equinox']
platforms = []

def get_connDevices(files_found, report_folder, seeker, wrap_text):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('devices.db'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    SELECT
    datetime(device_master.last_connected_time, 'unixepoch'),
    device_master.name,
    device_master.uuid, 
    device_master.favorite,
    device_master.visibility
    
    
    FROM device_master
    
    order by device_master.last_connected_time ASC
    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []  
    
    if usageentries > 0:
        for row in all_rows:
            data_list.append((row[0], row[1], row[2], row[3], row[4]))

        description = 'Connected Devices'
        report = ArtifactHtmlReport('Connected Devices')
        report.start_artifact_report(report_folder, 'Connected Devices', description)
        report.add_script()
        data_headers = ('Last Connected Time','Device Name', 'UUID', 'Is Favorite?', 'Is Visible?' )
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = 'Connected Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
        
        tlactivity = 'Connected Devices'
        timeline(report_folder, tlactivity, data_list, data_headers)
        
    else:
        logfunc('No device data available')
    
__artifacts__ = {
        "Connected Devices'": (
                "Connected Devices'",
                ('*/devices.db*'),
                get_connDevices)
}

        
        