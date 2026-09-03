__artifacts_v2__ = {
    "hyundaiCallHistory": {
        "name": "Hyundai - Call History",
        "description": "Bluetooth call history per connected phone from Hyundai/Kia infotainment CH_{mac}.db databases.",
        "author": "Nixy Camacho, @pmpulkownik",
        "version": "0.3",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-09-02",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Extracts call logs per device and derives device Bluetooth MAC directly from the database filename (CH_{mac}.db).",
        "paths": ('*/bluetooth/DB_BMS/CH_*.db*',),
        "output_types": "standard",
        "artifact_icon": "phone-call",
    }
}

import os
import re
import sqlite3
from datetime import datetime, timezone
from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc, open_sqlite_db_readonly


def _format_mac_from_filename(filename):
    """
    Extracts and formats MAC address from filename like CH_AABBCCDDEEFF.db -> AA:BB:CC:DD:EE:FF
    """
    base = os.path.basename(filename)
    stem = base.rsplit('.', 1)[0]
    raw_mac = stem[3:] if stem.startswith('CH_') else stem

    clean_hex = re.sub(r'[^A-Fa-f0-9]', '', raw_mac)
    if len(clean_hex) == 12:
        return ':'.join(clean_hex[i:i + 2] for i in range(0, 12, 2)).upper()
    return raw_mac.upper()


def _ts(value):
    if value is None or value == '' or value == 0:
        return ''
    if isinstance(value, (int, float)):
        if value > 1e11:
            value = value / 1000.0
        return convert_unix_ts_to_utc(value)
    text = str(value).strip()
    if text.isdigit():
        val = int(text)
        if val > 1e11:
            val = val / 1000.0
        return convert_unix_ts_to_utc(val)
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        return value


@artifact_processor
def hyundaiCallHistory(context):
    data_list = []
    source_paths = []

    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.db'):
            continue

        source_paths.append(file_found)
        device_mac = _format_mac_from_filename(file_found)
        db_filename = os.path.basename(file_found)

        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        try:
            cursor.execute('''
                SELECT 
                    date,
                    date_sort,
                    _id,
                    given_name,
                    family_name,
                    phone_number,
                    calltype,
                    duration,
                    numberType
                FROM bluetooth_callhistory
                ORDER BY date DESC
            ''')

            for row in cursor.fetchall():
                (
                    call_date,
                    date_sort,
                    rec_id,
                    given_name,
                    family_name,
                    phone_number,
                    calltype,
                    duration,
                    number_type
                ) = row

                name_parts = [str(p).strip() for p in (given_name, family_name) if p]
                full_name = ' '.join(name_parts) if name_parts else ''

                data_list.append((
                    _ts(call_date),
                    _ts(date_sort),
                    device_mac,
                    rec_id,
                    full_name,
                    given_name if given_name is not None else '',
                    family_name if family_name is not None else '',
                    phone_number if phone_number is not None else '',
                    calltype if calltype is not None else '',
                    duration if duration is not None else '',
                    number_type if number_type is not None else '',
                    db_filename
                ))
        except sqlite3.Error:
            pass

        db.close()

    data_headers = (
        ('Date (UTC)', 'datetime'),
        ('Date Sort (UTC)', 'datetime'),
        'Device MAC',
        'Record ID',
        'Full Name',
        'First Name',
        'Last Name',
        ('Phone Number', 'phonenumber'),
        'Call Type',
        'Duration (sec)',
        'Number Type',
        'Source Database'
    )

    source_repr = os.path.dirname(source_paths[0]) if source_paths else ''
    return data_headers, data_list, context.get_relative_path(source_repr)
