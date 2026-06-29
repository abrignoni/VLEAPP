__artifacts_v2__ = {
    "Device_Manager_Devices": {
        "name": "Device Manager Devices",
        "description": "Device manager history from Chrysler vehicles (DeviceManagerDeviceList "
                       "bz2-compressed sqlite).",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/*DeviceManagerDeviceList.bz*',),
        "output_types": "standard",
        "artifact_icon": "smartphone",
        "function": "get_devices",
    }
}

import bz2
import sqlite3

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def get_devices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with bz2.BZ2File(file_found) as f:
            db = sqlite3.connect(':memory:')
            db.deserialize(f.read())
            cursor = db.cursor()
            cursor.execute('SELECT name, address FROM DeviceListTable')
            for row in cursor.fetchall():
                data_list.append((row[0], row[1]))
            db.close()

    data_headers = ('Device Name', 'Address')
    return data_headers, data_list, context.get_relative_path(source_path)
