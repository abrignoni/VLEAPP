import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, logfunc, tsv, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Alfa Romeo','Giulia']
platforms = []

#This artifact parses contact information from the
#The test data we had was limited, so additional information may be added if more test data is gathered.

def get_Contacts(files_found, report_folder, seeker, wrap_text, time_offset):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('agenda.sqlite'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    Select
    ContactCard.FIRSTNAME,
    ContactCard.SURNAME,
    PhoneNumber.NUMBER,
    BT_Device.BD_ADDRESS
    from ContactCard
    left join BT_Device
    on ContactCard.BT_DEVICE_ID =  BT_Device.ID
    left join PhoneNumber
    on ContactCard.ID = PhoneNumber.CONTACT_ID
    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []  
    
    if usageentries > 0:
        for row in all_rows:
            data_list.append((row[0], row[1], row[2], row[3]))

        description = 'Alfa Romeo Contacts'
        report = ArtifactHtmlReport('Alfa Romeo Contacts')
        report.start_artifact_report(report_folder, 'Contacts', description)
        report.add_script()
        data_headers = ('First Name', 'Last Name', 'Phone Number', 'BT Address')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = 'Alfa_Romeo_Contacts'
        tsv(report_folder, data_headers, data_list, tsvname)
        
        #tlactivity = 'Alfa_Romeo_Contacts'
        #timeline(report_folder, tlactivity, data_list, data_headers)
    else:
        logfunc('No contact data available')
    


__artifacts__ = {
        "Alfa Romeo Contacts": (
                "Alfa Romeo Contacts",
                ('*/agenda.sqlite*'),
                get_Contacts)
}
        
        
