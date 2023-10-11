import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, logfunc, tsv, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Chevrolet','Equinox']
platforms = []

def get_contactsInfo(files_found, report_folder, seeker, wrap_text, time_offset):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('contact.db'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    SELECT
    contact_master.first_name,
    contact_master.middle_name,
    contact_master.last_name,
    phone_table.phone_number,
    contact_master.email_personal,
    contact_master.email_work,
    contact_master.email_organization,
    contact_master.email_other1,
    contact_master.email_other2,
    contact_master.org_name,
    contact_master.position_in_org,
    contact_master.birth_date,
    contact_master.note,
    contact_master.url,
    contact_master.category,
    contact_master.fax_number,
    address_table.addr_street,
    address_table.addr_city,
    address_table.addr_state,
    address_table.addr_zipcode,
    device_contact.device_id
    FROM contact_master
    left JOIN address_table
    
    ON address_table.contact_ID = contact_master.contact_ID
    left join phone_table
    ON phone_table.contact_ID = contact_master.contact_ID
    left join device_contact
    ON device_contact.contact_ID = contact_master.contact_ID
    ORDER by device_contact.device_id ASC
    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []  
    
    if usageentries > 0:
        for row in all_rows:
            data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20]))

        description = 'Contacts Information'
        report = ArtifactHtmlReport('Contacts Information')
        report.start_artifact_report(report_folder, 'Contacts', description)
        report.add_script()
        data_headers = ('First Name', 'Middle Name', 'Last Name', 'Phone Number', 'Personal Email', 'Work Email', 'Organization Email', 'Other Email 1', 'Other Email 2', 'Organization', 'Position in Organization', 'Date of Birth', 'Note', 'URL', 'Category', 'Fax', 'Street', 'City', 'State', 'Zip Code', 'Source Phone')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = 'Contacts'
        tsv(report_folder, data_headers, data_list, tsvname)
        
        tlactivity = 'Contacts'
        timeline(report_folder, tlactivity, data_list, data_headers)
    else:
        logfunc('No contacts data available')
    


__artifacts__ = {
        "Contacts": (
                "Contacts",
                ('*/contact.db*'),
                get_contactsInfo)
}
        
        