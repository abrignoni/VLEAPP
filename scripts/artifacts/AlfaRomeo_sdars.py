import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import timeline, logfunc, tsv, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Alfa Romeo','Giulia']
platforms = []

def get_sdarsInfo(files_found, report_folder, seeker, wrap_text, time_offset):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('agenda.sqlite'):
            break
            
    db = open_sqlite_db_readonly(file_found)
    cursor = db.cursor()
    cursor.execute('''
    Select
    siriusdata.value_name,
    siriusdata.value_description,
    siriusdata.value_string
    from siriusdata

    ''')

    all_rows = cursor.fetchall()
    usageentries = len(all_rows)
    data_list = []  
    
    if usageentries > 0:
        for row in all_rows:
            data_list.append((row[0], row[1], row[2]))

        description = 'Sirius Data'
        report = ArtifactHtmlReport('Alfa Romeo Sirius Settings')
        report.start_artifact_report(report_folder, 'Sirius Settings', description)
        report.add_script()
        data_headers = ('Name', 'Description', 'Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = 'AlfaRomeo_SiriusSettings'
        tsv(report_folder, data_headers, data_list, tsvname)
        
    else:
        logfunc('No Satellite Digital Audio Radio Service data available')
    


__artifacts__ = {
        "Alfa Romeo Sirius Data": (
                "Alfa Romeo Sirius Data",
                ('*/sdars_db.sqlite*'),
                get_sdarsInfo)
}
        
        
