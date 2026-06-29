__artifacts_v2__ = {
    "connDevices": {
        "name": "Connected Devices",
        "description": "Connected device history from a vehicle infotainment devices.db.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2021-07-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Connected Devices",
        "notes": "",
        "paths": ('*/devices.db*',),
        "output_types": "standard",
        "artifact_icon": "smartphone",
    }
}

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc, open_sqlite_db_readonly


@artifact_processor
def connDevices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('devices.db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT last_connected_time, name, uuid, favorite, visibility
            FROM device_master
            ORDER BY last_connected_time ASC
        ''')
        for row in cursor.fetchall():
            timestamp = convert_unix_ts_to_utc(row[0]) if row[0] is not None else ''
            data_list.append((timestamp, row[1], row[2], row[3], row[4]))
        db.close()

    data_headers = (('Last Connected Time', 'datetime'), 'Device Name', 'UUID', 'Is Favorite?',
                    'Is Visible?')
    return data_headers, data_list, context.get_relative_path(source_path)
