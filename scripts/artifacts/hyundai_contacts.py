import csv
import os
import sqlite3

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_contacts(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
                    
        cursor.execute("SELECT _id from bluetooth_contacts")
        ids = cursor.fetchall()
        #data_list.append(ids)

        cursor.execute("SELECT given_name from bluetooth_contacts")
        given_names = cursor.fetchall()
        #data_list.append(given_names)

        cursor.execute("SELECT family_name from bluetooth_contacts")
        family_names = cursor.fetchall()
        #data_list.append(family_names)

        cursor.execute("SELECT phone_number from bluetooth_contacts")
        phone_number = cursor.fetchall()
        #data_list.append(phone_number)

        i = 0
        for id in ids:
            data_list.append((ids[i], given_names[i], family_names[i], phone_number[i]))
            i += 1
                    
        data_list.append((ids, given_names, family_names, phone_number))
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Contact Data')
        report.start_artifact_report(report_folder, f'Contact Data')
        report.add_script()
        data_headers = ('ID','given_name', 'family_name', 'phone_number')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Contact Data'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Contact Data found')

__artifacts__ = {
    "contacts": (
        "contacts",
        ('*/bluetooth/DB_BMS/MC_*.db'),
        get_contacts),
}