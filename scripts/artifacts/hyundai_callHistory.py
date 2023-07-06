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
        

        cursor.execute("SELECT _id from bluetooth_callhistory")
        ids = cursor.fetchall()
        #data_list.append(ids)

        cursor.execute("SELECT given_name from bluetooth_callhistory")
        givens = cursor.fetchall()
        #data_list.append(givens)

        cursor.execute("SELECT family_name from bluetooth_callhistory")
        familys = cursor.fetchall()
        #data_list.append(familys)

        cursor.execute("SELECT phone_number from bluetooth_callhistory")
        phone_numbers = cursor.fetchall()
        #data_list.append(phone_numbers)

        cursor.execute("SELECT calltype from bluetooth_callhistory")
        callTypes = cursor.fetchall()
        #data_list.append(callTypes)

        cursor.execute("SELECT date from bluetooth_callhistory")
        dates = cursor.fetchall()
        #data_list.append(dates)

        cursor.execute("SELECT date_sort from bluetooth_callhistory")
        date_sorts = cursor.fetchall()
        #data_list.append(date_sorts)

        cursor.execute("SELECT duration from bluetooth_callhistory")
        durations = cursor.fetchall()
        #data_list.append(durations)

        cursor.execute("SELECT numberType from bluetooth_callhistory")
        numberTypes = cursor.fetchall()
        #data_list.append(numberTypes)
        i = 0

    #append array for each column to data_list, push data_list to report
        data_list.append((ids, givens, familys, phone_numbers, callTypes, dates, date_sorts, durations, numberTypes))
                    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Call History')
        report.start_artifact_report(report_folder, f'Call History')
        report.add_script()
        data_headers = ('id','given_name', 'family_name', 'phone_number', 'calltype', 'date', 'date_sort', 'duration', 'numberType')
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