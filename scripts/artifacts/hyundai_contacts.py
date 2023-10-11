import csv
import os
import sqlite3
import re

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_contacts(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        db = open_sqlite_db_readonly(file_found)
        db_name = os.path.splittext(file_found)
        cursor = db.cursor()
                    
        cursor.execute("SELECT _id from bluetooth_contacts")
        ids = cursor.fetchall()

        cursor.execute("SELECT given_name from bluetooth_contacts")
        given_names = cursor.fetchall()

        cursor.execute("SELECT family_name from bluetooth_contacts")
        family_names = cursor.fetchall()

        cursor.execute("SELECT phone_number from bluetooth_contacts")
        phone_number = cursor.fetchall()

        ti = []
        tg = []
        tf = []
        tn = []

        i = 0
        for id in ids:
            id = str(id)
            id = re.sub(r'\W+', '', id)
            ti.append(id)

        for given in given_names:
            given = str(given)
            given = re.sub(r'\W+', '', given)
            tg.append(given)
        for family in family_names:
            family = str(family)
            family = re.sub(r'\W+', '', family)
            tf.append(family)
        for number in phone_number:
            number = str(number)
            number = re.sub(r'\W+', '', number)
            tn.append(number)
        
        for id in ids:
            data_list.append((ti[i], tg[i], tf[i], tn[i]))
            i += 1
        if db_name[1] == 'db':
            break
                    
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
        ('*/bluetooth/DB_BMS/MC_*.db*'),
        get_contacts),
}