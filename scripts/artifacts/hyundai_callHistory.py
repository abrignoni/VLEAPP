import csv
import os
import sqlite3
import re

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_callHistory(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        db = open_sqlite_db_readonly(file_found)
        db_name = os.path.splittext(file_found)
        cursor = db.cursor()
        

        cursor.execute("SELECT _id from bluetooth_callhistory")
        ids = cursor.fetchall()

        cursor.execute("SELECT given_name from bluetooth_callhistory")
        givens = cursor.fetchall()

        cursor.execute("SELECT family_name from bluetooth_callhistory")
        familys = cursor.fetchall()

        cursor.execute("SELECT phone_number from bluetooth_callhistory")
        phone_numbers = cursor.fetchall()

        cursor.execute("SELECT calltype from bluetooth_callhistory")
        callTypes = cursor.fetchall()


        cursor.execute("SELECT date from bluetooth_callhistory")
        dates = cursor.fetchall()

        cursor.execute("SELECT date_sort from bluetooth_callhistory")
        date_sorts = cursor.fetchall()

        cursor.execute("SELECT duration from bluetooth_callhistory")
        durations = cursor.fetchall()

        cursor.execute("SELECT numberType from bluetooth_callhistory")
        numberTypes = cursor.fetchall()
        i = 0

        ti = []
        tg = []
        tf = []
        tn = []
        tc = []
        td = []
        tds = []
        tdu = []
        tnt = []
        
        for id in ids:
            id = str(id)
            id = re.sub(r'\W+', '', id)
            ti.append(id)
        for given in givens:
            given = str(given)
            given = re.sub(r'\W+', '', given)
            tg.append(given)
        for family in familys:
            family = str(family)
            family = re.sub(r'\W+', '', family)
            tf.append(family)
        for number in phone_numbers:
            number = str(number)
            number = re.sub(r'\W+', '', number)
            tn.append(number)
        for ct in callTypes:
            ct = str(ct)
            ct = re.sub(r'\W+', '', ct)
            tc.append(ct)
        for date in dates:
            date = str(date)
            date = re.sub(r'\W+', '', date)
            td.append(date)
        for ds in date_sorts:
            ds = str(ds)
            ds = re.sub(r'\W+', '', ds)
            tds.append(ds)
        for duration in durations:
            duration = str(duration)
            duration = re.sub(r'\W', '', duration)
            tdu.append(duration)
        for nt in numberTypes:
            nt = str(nt)
            nt = re.sub(r'\W', '', nt)
            tnt.append(nt)
        if db_name[1] == 'db':
            break


    #append array for each column to data_list, push data_list to report
        for id in ids:
            data_list.append((ti[i], tg[i], tf[i], tn[i], tc[i], td[i], tds[i], tdu[i], tnt[i]))
            i += 1
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
        ('*/bluetooth/DB_BMS/CH_*.db*'),
        get_callHistory),
}