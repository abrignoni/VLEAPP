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
from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


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


@artifact_processor
def hyundaiContacts(context):
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
                    _id,
                    given_name,
                    family_name,
                    phone_number,
                    phone_type
                FROM bluetooth_contacts
                ORDER BY _id ASC
            ''')

            for row in cursor.fetchall():
                rec_id, given_name, family_name, phone_number, phone_type = row

                # Build full name cleanly if names are present
                name_parts = [str(p).strip() for p in (given_name, family_name) if p]
                full_name = ' '.join(name_parts) if name_parts else ''

                data_list.append((
                    device_mac,
                    rec_id,
                    full_name,
                    given_name if given_name is not None else '',
                    family_name if family_name is not None else '',
                    phone_number if phone_number is not None else '',
                    phone_type if phone_type is not None else '',
                    db_filename
                ))
        except sqlite3.Error:
            pass

        db.close()

    data_headers = (
        'Device MAC',
        'Record ID',
        'Full Name',
        'First Name',
        'Last Name',
        ('Phone Number', 'phonenumber'),
        'Phone Type',
        'Source Database'
    )

    source_repr = os.path.dirname(source_paths[0]) if source_paths else ''
    return data_headers, data_list, context.get_relative_path(source_repr)
