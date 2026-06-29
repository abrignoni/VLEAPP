__artifacts_v2__ = {
    "PhoneBook_Devices": {
        "name": "PhoneBook Devices",
        "description": "Phonebook BT device list with connect/disconnect times from Chrysler "
                       "vehicles (PhoneBookDeviceList bz2-compressed sqlite).",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "Last Connected / Last Disconnected interpreted as Unix epochs and normalized to "
                 "UTC; non-numeric values kept as stored.",
        "paths": ('*/*PhoneBookDeviceList.bz*',),
        "output_types": "standard",
        "artifact_icon": "phone",
        "function": "get_phone_book_devices",
    }
}

import bz2
import sqlite3
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc


def _ts(value):
    if value is None or value == '':
        return ''
    if isinstance(value, (int, float)):
        return convert_unix_ts_to_utc(value)
    text = str(value).strip()
    if text.isdigit():
        return convert_unix_ts_to_utc(int(text))
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        return value


@artifact_processor
def get_phone_book_devices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with bz2.BZ2File(file_found) as f:
            db = sqlite3.connect(':memory:')
            db.deserialize(f.read())
            cursor = db.cursor()
            cursor.execute('SELECT DeviceAddress, LastConnected, LastDisconnected FROM T_BTDevice')
            for row in cursor.fetchall():
                data_list.append((row[0], _ts(row[1]), _ts(row[2])))
            db.close()

    data_headers = ('Device Mac Address', ('Last Connected', 'datetime'),
                    ('Last Disconnected', 'datetime'))
    return data_headers, data_list, context.get_relative_path(source_path)
