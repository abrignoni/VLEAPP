__artifacts_v2__ = {
    "hyundaiCallHistory": {
        "name": "Hyundai - Call History",
        "description": "Bluetooth call history per connected phone from Hyundai/Kia infotainment CH_{mac}.db databases.",
        "author": "Nixy Camacho, @pmpulkownik",
        "version": "0.3",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-09-03",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Extracts call logs per device and derives device Bluetooth MAC directly from the database filename (CH_{mac}.db). Validated against a single Hyundai/Kia head unit from an extraction that could not be shared publicly, so no test fixture accompanies this artifact.",
        "paths": ('*/bluetooth/DB_BMS/CH_*.db*',),
        "output_types": "standard",
        "artifact_icon": "phone-call",
    }
}

import os
import re
import sqlite3
from datetime import datetime, timezone

from scripts.ilapfuncs import (artifact_processor, convert_unix_ts_to_utc, logfunc,
                               open_sqlite_db_readonly)

# Ordered as queried. A column missing from a phone's database is reported empty
# rather than costing that phone every row -- see _present_columns.
_CALL_COLUMNS = ('date', 'date_sort', '_id', 'given_name', 'family_name', 'phone_number',
                 'calltype', 'duration', 'numberType')


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


def _present_columns(cursor, table, wanted):
    """
    The wanted columns this table actually carries, in the order given.

    Firmware versions differ in what these tables hold, and a SELECT naming a
    column the table lacks fails the whole statement. Selecting only what is
    present costs the absent column rather than every call on that phone.
    """
    try:
        cursor.execute(f'PRAGMA table_info({table})')
        present = {row[1] for row in cursor.fetchall()}
    except sqlite3.Error:
        return []
    return [column for column in wanted if column in present]


def _value(record, column):
    """The stored value, or '' when the column is absent or NULL."""
    value = record.get(column)
    return '' if value is None else value


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
        if os.path.isdir(file_found) or not file_found.endswith('.db'):
            continue

        device_mac = _format_mac_from_filename(file_found)
        db_filename = os.path.basename(file_found)

        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        cursor = db.cursor()

        columns = _present_columns(cursor, 'bluetooth_callhistory', _CALL_COLUMNS)
        if not columns:
            logfunc(f"{db_filename}: no bluetooth_callhistory table, skipped")
            db.close()
            continue

        statement = f'SELECT {", ".join(columns)} FROM bluetooth_callhistory'
        if 'date' in columns:
            statement += ' ORDER BY date DESC'

        try:
            cursor.execute(statement)
            rows = cursor.fetchall()
        except sqlite3.Error as ex:
            logfunc(f"{db_filename}: reading bluetooth_callhistory failed, skipped")
            logfunc(f" - {str(ex)}")
            db.close()
            continue

        db.close()
        source_paths.append(file_found)

        missing = [column for column in _CALL_COLUMNS if column not in columns]
        if missing:
            logfunc(f"{db_filename}: reported without {', '.join(missing)}")

        for row in rows:
            record = dict(zip(columns, row))
            given_name = _value(record, 'given_name')
            family_name = _value(record, 'family_name')

            name_parts = [str(p).strip() for p in (given_name, family_name) if p]
            full_name = ' '.join(name_parts) if name_parts else ''

            data_list.append((
                _ts(record.get('date')),
                _ts(record.get('date_sort')),
                device_mac,
                _value(record, '_id'),
                full_name,
                given_name,
                family_name,
                _value(record, 'phone_number'),
                _value(record, 'calltype'),
                _value(record, 'duration'),
                _value(record, 'numberType'),
                db_filename
            ))

    data_headers = (
        ('Date (UTC)', 'datetime'),
        ('Date Sort (UTC)', 'datetime'),
        'Device MAC',
        'Record ID',
        'Full Name',
        'First Name',
        'Last Name',
        ('Phone Number', 'phonenumber'),
        'Call Type (as stored)',
        'Duration (as stored)',
        'Number Type (as stored)',
        'Source Database'
    )

    return data_headers, data_list, '\n'.join(source_paths)
