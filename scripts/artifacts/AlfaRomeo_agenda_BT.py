__artifacts_v2__ = {
    "alfaRomeoBtSync": {
        "name": "Alfa Romeo - Bluetooth Last Sync",
        "description": "Bluetooth device last-sync times from an Alfa Romeo agenda.sqlite.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2023-06-16",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Alfa Romeo Vehicles",
        "notes": "Last Sync Date is interpreted as a Unix epoch (auto-detected seconds/ms) and "
                 "normalized to UTC; non-numeric values are kept as stored.",
        "paths": ('*/agenda.sqlite*',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    }
}

from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc, open_sqlite_db_readonly


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
def alfaRomeoBtSync(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('agenda.sqlite'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT BT_DEVICE.LAST_SYNC, BT_DEVICE.BD_ADDRESS
            FROM BT_Device
            ORDER BY BT_DEVICE.LAST_SYNC ASC
        ''')
        for row in cursor.fetchall():
            data_list.append((_ts(row[0]), row[1]))
        db.close()

    data_headers = (('Last Sync Date', 'datetime'), 'BT Address')
    return data_headers, data_list, context.get_relative_path(source_path)
