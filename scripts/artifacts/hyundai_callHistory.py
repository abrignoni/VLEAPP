__artifacts_v2__ = {
    "hyundaiCallHistory": {
        "name": "Hyundai - Call History",
        "description": "Bluetooth call history from a Hyundai infotainment CH_*.db.",
        "author": "Nixy Camacho",
        "version": "0.2",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Rewritten as a single query (the original ran nine separate SELECTs and crashed on "
                 "os.path.splittext). date / date_sort are interpreted as Unix epochs and "
                 "normalized to UTC.",
        "paths": ('*/bluetooth/DB_BMS/CH_*.db*',),
        "output_types": "standard",
        "artifact_icon": "phone-call",
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
def hyundaiCallHistory(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT _id, given_name, family_name, phone_number, calltype, date, date_sort,
                   duration, numberType
            FROM bluetooth_callhistory
        ''')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2], row[3], row[4], _ts(row[5]), _ts(row[6]),
                              row[7], row[8]))
        db.close()

    data_headers = ('id', 'given_name', 'family_name', ('phone_number', 'phonenumber'), 'calltype',
                    ('date', 'datetime'), ('date_sort', 'datetime'), 'duration', 'numberType')
    return data_headers, data_list, context.get_relative_path(source_path)
