import csv
import os
import scripts.artifacts.artGlobals 

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Ford Mustang','F-150']
platforms = ['SYNC3.2V2','SYNCGen3.0_3.0.18093_PRODUCT','SyncGen3_v2_b', 'SYNCGen3.0_1.0.15139_PRODUCT']

def get_nvcaContacts(files_found, report_folder, seeker, wrap_text):
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('.sqlite'):
            db = open_sqlite_db_readonly(file_found)
            cursor = db.cursor()
            cursor.execute('''
            select 
            First_Name,
            Last_Name, 
            Phone_Number, 
            Phone_Number_Type
            from S_Phone_Number_Type, t_phone_number
            where S_Phone_Number_Type.S_Phone_Number_Type_id = t_phone_number.S_Phone_Number_Type_Id
            ''')
            
            all_rows = cursor.fetchall()
            usageentries = len(all_rows)
            data_list = []  
            
            if usageentries > 0:
                for row in all_rows:
                    data_list.append((row[0], row[1], row[2], row[3],))
                
                basefile = os.path.basename(file_found)
                
                description = 'Nuance VCA Contacts phone numbers.'
                report = ArtifactHtmlReport('Nuance VCA Contacts')
                report.start_artifact_report(report_folder, f'{basefile} Contacts', description)
                report.add_script()
                data_headers = ('First Name', 'Last Name', 'Phone Number', 'Type')
                report.write_artifact_data_table(data_headers, data_list, file_found)
                report.end_artifact_report()
                
                tsvname = f'{basefile} Contacts'
                tsv(report_folder, data_headers, data_list, tsvname)
            else:
                logfunc('No Nuance VCA Contacts data available')

        