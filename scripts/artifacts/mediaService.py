import sqlite3
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows, open_sqlite_db_readonly

#Compatability Data
vehicles = ['Ford']
platforms = ['SYNC3.1','SYNCGen3']

def get_mediaService(files_found, report_folder, seeker, wrap_text, time_offset):
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('mediaservice_db'):
            db = open_sqlite_db_readonly(file_found)
            cursor = db.cursor()
            cursor.execute('''
            select
            mediastores.btdeviceid as "BT Device ID",
            mediastores.serial as "Serial",
            mediastores.device_id as "Device ID",
            mediastores.manufacturer as "Manufacturer",
            mediastores.product as "Product",
            mediastores.device_name as "Device Name",
            mediastores.vendorid as "Vendor ID",
            mediastores.productid as "Product ID",
            Case mediastores.attached
                when '0' then 'No'
                when '1' then 'Yes'
                ELSE 'Not Specified'
            END as "Device Attached",
            Case mediastores.active_onshutdown
                when '0' then 'No'
                when '1' then 'Yes'
                ELSE 'Not Specified'
            END as "Active On Shutdown?",
            Case mediastores.remote
                when '0' then 'No'
                when '1' then 'Yes'
                ELSE 'Not Specified'
            END as "Is Remote?",
            mediastores.fs_type as "FS Type"
            from mediastores
            order by mediastores.btdeviceid
            ''')
            
            all_rows = cursor.fetchall()
            usageentries = len(all_rows)
            data_list = []  
            
            if usageentries > 0:
                for row in all_rows:
                    data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11]))
                
                basefile = os.path.basename(file_found)
                
                description = 'Media Service Information'
                report = ArtifactHtmlReport('Media Service Information')
                report.start_artifact_report(report_folder, f'Media Service Information', description)
                report.add_script()
                data_headers = ('BT Device ID', 'Serial', 'Device ID', 'Manufacturer', 'Product', 'Device Name', 'Vendor ID', 'Product ID', 'Device Attached', 'Active on Shutdown', 'Is Remote', 'FS Type')
                report.write_artifact_data_table(data_headers, data_list, file_found)
                report.end_artifact_report()
                
                tsvname = f'{basefile} Media Service Information'
                tsv(report_folder, data_headers, data_list, tsvname)
            else:
                logfunc('No Media Service Information data available')

    
__artifacts__ = {
        "mediaservice": (
                "Media Service",
                ('*/mediaservice_db*'),
                get_mediaService)
}
