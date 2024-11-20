__artifacts_v2__ = {
    "Proj_Ctrl_Devices": {
        "name": "Proj Ctrl Devices",
        "description": "Scrapes the Proj Ctrl data from Chrysler Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-11-18",  # Date of the latest version
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/sal_bkup/proj_ctrl'),
        "function": "get_proj_ctrl_devices"
    }
}

import csv
import os
import re
import bz2
import sqlite3

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['FCA','Grand Cherokee']
platforms = ['']

def get_proj_ctrl_devices(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        devAddr = []
        devFriendlyName = []
    
        db = open_sqlite_db_readonly(file_found)
        #db.deserialize(f.read())
        cursor = db.cursor()
        cursor.execute('''
        Select
        device_type, attach_order, name, serial_number, bt_mac_address, port_id, attached_count
        From devicelist
        ''')
        all_rows = cursor.fetchall()
        
        usageentries = len(all_rows)
        data_list = []  
        
        if usageentries > 0:
            for row in all_rows:
                data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
 

    if len(data_list) > 0: # Check to see if Data Found
        report = ArtifactHtmlReport('Proj Ctrl Devices')
        report.start_artifact_report(report_folder, f'Proj Ctrl Devices')
        report.add_script()
        data_headers = ("Device Type", "Attach Order", "Name", "Serial Number", "BT Mac Address", "Port Id", "Attached Count")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Proj Ctrl Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Proj Ctrl found')

