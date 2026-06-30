__artifacts_v2__ = {
    "Proj_Ctrl_Devices": {
        "name": "Chrysler - Proj Ctrl Devices",
        "description": "Device list (type, name, serial, BT MAC, port, attach count) from a "
                       "Chrysler sal_bkup/proj_ctrl SQLite database.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/sal_bkup/proj_ctrl',),
        "output_types": "standard",
        "artifact_icon": "list",
        "function": "get_proj_ctrl_devices",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def get_proj_ctrl_devices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
        SELECT device_type, attach_order, name, serial_number, bt_mac_address, port_id,
        attached_count
        FROM devicelist
        ''')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
        db.close()

    data_headers = ('Device Type', 'Attach Order', 'Name', 'Serial Number', 'BT Mac Address',
                    'Port Id', 'Attached Count')
    return data_headers, data_list, context.get_relative_path(source_path)
