__artifacts_v2__ = {
    "hyundaiContacts": {
        "name": "Hyundai - Bluetooth Contacts",
        "description": "Bluetooth contacts per connected phone from Hyundai/Kia infotainment MC_{mac}.db databases.",
        "author": "Nixy Camacho, @pmpulkownik",
        "version": "0.3",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-09-02",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Extracts contacts per device and derives device Bluetooth MAC address directly from the database filename (MC_{mac}.db).",
        "paths": ('*/bluetooth/DB_BMS/MC_*.db*',),
        "output_types": "standard",
        "artifact_icon": "users",
    }
}

import os
import re
import sqlite3

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

# Ordered as reported. A column missing from a phone's database is reported empty
# rather than costing that phone every row -- see _present_columns.
_CONTACT_COLUMNS = ('_id', 'given_name', 'family_name', 'phone_number', 'phone_type')


def _format_mac_from_filename(filename):
    """
    Extracts and formats MAC address from filename like MC_AABBCCDDEEFF.db -> AA:BB:CC:DD:EE:FF
    """
    base = os.path.basename(filename)
    stem = base.rsplit('.', 1)[0]
    raw_mac = stem[3:] if stem.startswith('MC_') else stem

    clean_hex = re.sub(r'[^A-Fa-f0-9]', '', raw_mac)
    if len(clean_hex) == 12:
        return ':'.join(clean_hex[i:i + 2] for i in range(0, 12, 2)).upper()
    return raw_mac.upper()


def _present_columns(cursor, table, wanted):
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


@artifact_processor
def hyundaiContacts(context):
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

        columns = _present_columns(cursor, 'bluetooth_contacts', _CONTACT_COLUMNS)
        if not columns:
            logfunc(f"{db_filename}: no bluetooth_contacts table, skipped")
            db.close()
            continue

        statement = f'SELECT {", ".join(columns)} FROM bluetooth_contacts'
        if '_id' in columns:
            statement += ' ORDER BY _id ASC'

        try:
            cursor.execute(statement)
            rows = cursor.fetchall()
        except sqlite3.Error as ex:
            logfunc(f"{db_filename}: reading bluetooth_contacts failed, skipped")
            logfunc(f" - {str(ex)}")
            db.close()
            continue

        db.close()
        source_paths.append(file_found)

        missing = [column for column in _CONTACT_COLUMNS if column not in columns]
        if missing:
            logfunc(f"{db_filename}: reported without {', '.join(missing)}")

        for row in rows:
            record = dict(zip(columns, row))
            given_name = _value(record, 'given_name')
            family_name = _value(record, 'family_name')

            # Build full name cleanly if names are present
            name_parts = [str(p).strip() for p in (given_name, family_name) if p]
            full_name = ' '.join(name_parts) if name_parts else ''

            data_list.append((
                device_mac,
                _value(record, '_id'),
                full_name,
                given_name,
                family_name,
                _value(record, 'phone_number'),
                _value(record, 'phone_type'),
                db_filename
            ))

    data_headers = (
        'Device MAC',
        'Record ID',
        'Full Name',
        'First Name',
        'Last Name',
        ('Phone Number', 'phonenumber'),
        'Phone Type (as stored)',
        'Source Database'
    )

    return data_headers, data_list, '\n'.join(source_paths)
