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
        cursor.execute('''
            SELECT
            FROM
            NAME
            FROM SQLITE_SCHEMA
            WHERE NAME LIKE ''
            order by name
            '''
        )
        all_rows = cursor.fetchall()
        usageentries = len(all_rows)
        if usageentries > 0:
            for row in all_rows:
                data_list = []
                data_list_as_is = []
                    
                tablename = (row[0])
                tablenamenum = tablename.split('_')[2]
                    
                cursor.execute(f''' 
                    SELECT
                    num_phonebook_{tablenamenum}.entry_id,
                    phonebook_{tablenamenum}.first_name,
                    phonebook_{tablenamenum}.last_name,
                    GROUP_CONCAT(num_phonebook_{tablenamenum}.number, '; ')
                    from num_phonebook_{tablenamenum}
                    join phonebook_{tablenamenum} where num_phonebook_{tablenamenum}.entry_id = phonebook_{tablenamenum}.entry_id
                    group by num_phonebook_{tablenamenum}.entry_id
                    ''')
                    
                all_rows_inner = cursor.fetchall()
                usageentries_inner = len(all_rows_inner)
                    
                if usageentries_inner > 0:
                    for rows_inner in all_rows_inner:
                        data_list.append((rows_inner[0], rows_inner[1], rows_inner[2], rows_inner[3].replace(';', '<br>')))
                        data_list_as_is.append((rows_inner[0], rows_inner[1], rows_inner[2], rows_inner[3]))
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Contact Data')
        report.start_artifact_report(report_folder, f'Contact Data')
        report.add_script()
        data_headers = ('ID','Value')
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