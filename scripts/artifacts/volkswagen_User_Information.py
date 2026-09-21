__artifacts_v2__ = {
    "VW_MIB2_User_Info": {
        "name": "User Info",
        "description": "Retrieve user-related data from Volkswagen Vehicles",
        "author": "@posiwer",
        "version": "1.0",
        "date": "2026-01-05",
        "requirements": "none",
        "category": "Volkswagen Vehicle",
        "notes": "Updated to include contact photos when available",
        "paths": ('*/*db00000*', '*/*photo*'),
        "function": "get_User_Information"
    }
}

import os
import sqlite3
import json
import shutil
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import tsv

def get_User_Information(files_found, report_folder, seeker, wrap_text, time_offset):
    db_file = None
    photo_files = []
    
    for file in files_found:
        if file.endswith('db0000060'):
            db_file = file
        elif file.lower().endswith('.jpg'):
            photo_files.append(file)
    
    if not db_file:
        return

    photos_dir = os.path.join(report_folder, 'Contact Photos')
    os.makedirs(photos_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            pt.persID,
            prt.profileID as deviceID,
            prt.profileName AS deviceName,
            pt.pictureID,
            UPPER(
                SUBSTR(prt.macAddress, 1, 2) || ':' ||
                SUBSTR(prt.macAddress, 3, 2) || ':' ||
                SUBSTR(prt.macAddress, 5, 2) || ':' ||
                SUBSTR(prt.macAddress, 7, 2) || ':' ||
                SUBSTR(prt.macAddress, 9, 2) || ':' ||
                SUBSTR(prt.macAddress, 11, 2)
            ) AS MacAddress,
            pnt.phoneNumber,
            COALESCE(gt2.graphem, '') || 
            CASE 
                WHEN gt1.graphem IS NOT NULL AND gt2.graphem IS NOT NULL THEN ' ' 
                ELSE '' 
            END || 
            COALESCE(gt1.graphem, '') AS fullName,
            pt.pictureType AS hasPicture
        FROM phoneNumberTable AS pnt
        LEFT JOIN personalTable AS pt ON pt.persID = pnt.persID
        LEFT JOIN graphemTable AS gt1 ON pt.lastNameGraphem = gt1.graphemID
        LEFT JOIN graphemTable AS gt2 ON pt.firstNameGraphem = gt2.graphemID
        LEFT JOIN profileTable AS prt ON pt.profileID = prt.profileID;
    ''')
    
    contacts = cursor.fetchall()

    contact_data = []
    extracted_photos = 0
    
    for contact in contacts:
        picture_id = str(contact['pictureID'])
        pers_id = contact['persID']
        full_name = contact['fullName'] or "Unknown Contact"
        phone_number = contact['phoneNumber'] or "No Number"
        device_name = contact['deviceName'] or "Unknown Device"
        
        safe_name = "".join(c for c in full_name if c.isalnum() or c in (' ', '_')).strip()
        safe_name = safe_name.replace(' ', '_') if safe_name else f"Contact {pers_id}"
        
        matching_photos = [
            f for f in photo_files 
            if picture_id in os.path.basename(f).lower()
        ]
        
        photo_html = "Photo not Associated"
        if matching_photos:
            source_photo = matching_photos[0]
            
            dest_filename = f"{device_name}_{safe_name}_{phone_number}_{picture_id}.jpg"
            dest_path = os.path.join(photos_dir, dest_filename)
            
            shutil.copy2(source_photo, dest_path)
            relative_path = os.path.join('Volkswagen Vehicle/Contact Photos', dest_filename)
            photo_html = f'<a href="{relative_path}" target="_blank"><img src="{relative_path}" height="100"></a>'
            extracted_photos += 1
        
        contact_data.append({
            'Device': device_name,
            'Name': full_name,
            'Phone': phone_number,
            'PhotoID': picture_id,
            'Photo': photo_html,
            'PersID': pers_id
        })


    if contact_data:
        headers = ['Device', 'Name', 'Phone', 'PhotoID', 'Photo']
        data_list = [
            [item['Device'], item['Name'], item['Phone'], item['PhotoID'], item['Photo']]
            for item in contact_data
        ]
        
        report = ArtifactHtmlReport('Phone Numberss')
        report.start_artifact_report(report_folder, 'Phone Numbers')
        report.add_script()
        report.write_artifact_data_table(headers, data_list, db_file, html_escape=False)
        report.end_artifact_report()
        
        tsv_data = [
            [item['Device'], item['Name'], item['Phone'], item['PhotoID'], 
             'Yes' if 'href' in item['Photo'] else 'No']
            for item in contact_data
        ]
        tsv(report_folder, headers, tsv_data, 'Phone Numbers')
        
        json_data = []
        for item in contact_data:
            json_item = {
                'Device': item['Device'],
                'Name': item['Name'],
                'Phone': item['Phone'],
                'PhotoID': item['PhotoID'],
                'PhotoExtracted': 'Yes' if 'href' in item['Photo'] else 'No',
                'PersID': item['PersID']
            }
            if 'href' in item['Photo']:
                json_item['PhotoPath'] = os.path.join('Contact Photos', 
                    f"{item['Device']}_{item['Name'].replace(' ', '_')}_{item['Phone']}_{item['PhotoID']}.jpg")
            json_data.append(json_item)
        
        json_path = os.path.join(report_folder, 'contacts_with_photos.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)


    cursor.execute('''
        SELECT
            ldt.lastDestinationID,
            ldt.navLocID,
            ldt.hashCode AS destinationHash,
            ldt.name AS destinationName,
            ldt.status AS destinationStatus,
            nht.countryAbbreviation,
            nht.dbVersion,
            nht.flags,
            nht.name AS historyName,
            nht.hash AS historyHash,
            nht.status AS historyStatus,
            nlt.navData
        FROM lastDestinationTable AS ldt
        LEFT JOIN navHistoryTable AS nht ON ldt.navLocID = nht.navLocID
        LEFT JOIN navLocationTable AS nlt ON ldt.navLocID = nlt.navID;
    ''')

    nav_data_rows = cursor.fetchall()

    if len(nav_data_rows) > 0:
        nav_headers = [
            'Last Destination ID',
            'Nav Location ID',
            'Destination Hash',
            'Destination Name',
            'Destination Status',
            'Country Abbreviation',
            'Database Version',
            'Flags',
            'History Name',
            'History Hash',
            'History Status',
            'Nav Data'
        ]

        nav_data_list = []
        for row in nav_data_rows:
            row_dict = dict(zip(nav_headers, row))
            if row_dict['Nav Data'] is not None:
                try:
                    row_dict['Nav Data'] = row_dict['Nav Data'].decode('utf-8', errors='replace')
                except AttributeError:
                    row_dict['Nav Data'] = str(row_dict['Nav Data'])
            nav_data_list.append([str(value) if value is not None else '' for value in row_dict.values()])

        nav_report = ArtifactHtmlReport('Navigation Data')
        nav_report.start_artifact_report(report_folder, 'Navigation Data')
        nav_report.add_script()
        nav_report.write_artifact_data_table(nav_headers, nav_data_list, db_file)
        nav_report.end_artifact_report()

        tsv(report_folder, nav_headers, nav_data_list, 'Navigation Data')

        json_path = os.path.join(report_folder, 'navigation_data.json')
        with open(json_path, mode='w', encoding='utf-8') as json_file:
            json.dump(nav_data_list, json_file, indent=4, ensure_ascii=False)

    conn.close()