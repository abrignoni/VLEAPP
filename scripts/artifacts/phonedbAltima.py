import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, tsv, logfunc, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Nissan Altima',]
platforms = []

def get_phonedbAltima(files_found, report_folder, seeker, wrap_text, time_offset):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('phone_db.db'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
        SELECT 
        NAME 
        FROM SQLITE_SCHEMA
        WHERE NAME LIKE 'NUM_PHONEBOOK%'
        order by name
    ''')

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
                    
                description = 'Phone Book Contactrs'
                report = ArtifactHtmlReport(f'Phone Book {tablenamenum} Contacts')
                report.start_artifact_report(report_folder, f'Phone Book {tablenamenum} Contacts', description)
                report.add_script()
                data_headers = ('ID', 'First Name', 'Last Name', 'Phone Number/s')
                report.write_artifact_data_table(data_headers, data_list, file_found, html_no_escape=['Phone Number/s'])
                report.end_artifact_report()
                
                tsvname = f'Phone Book Information {tablenamenum}'
                tsv(report_folder, data_headers, data_list_as_is, tsvname)
                
            else:
                logfunc(f'No Phone Book {tablenamenum} Contacts data available')
                
    else:
        logfunc('No Phone Book contacts data available')
    


__artifacts__ = {
        "Phone Book": (
                "Phone Book DB",
                ('*/ffs/phone_db.db*'),
                get_phonedbAltima)
}
        
        