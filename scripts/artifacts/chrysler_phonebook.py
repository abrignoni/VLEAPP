__artifacts_v2__ = {
    "PhoneBook_Devices": {
        "name": "PhoneBook Devices",
        "description": "Scrapes the Phonebook data from Chrysler Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-10-09",  # Date of the latest version
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/*PhoneBookDeviceList.bz*'),
        "function": "get_phone_book_devices"
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

def get_phone_book_devices(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        devAddr = []
        devFriendlyName = []
        with bz2.BZ2File(file_found) as f:   
            db = sqlite3.Connection(":memory:")
            db.deserialize(f.read())
            cursor = db.cursor()
            cursor.execute('''
            Select
            DeviceAddress, LastConnected, LastDisconnected
            From T_BTDevice
            ''')
            all_rows = cursor.fetchall()
            
            usageentries = len(all_rows)
            data_list = []  
            
            if usageentries > 0:
                for row in all_rows:
                    data_list.append((row[0], row[1], row[2]))
 

    if len(data_list) > 0: # Check to see if Data Found
        report = ArtifactHtmlReport('PhoneBook Devices')
        report.start_artifact_report(report_folder, f'PhoneBook Devices')
        report.add_script()
        data_headers = ("Device Mac Address", "Last Connected", "Last Disconnected")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'PhoneBook Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No PhoneBook Devices found')

