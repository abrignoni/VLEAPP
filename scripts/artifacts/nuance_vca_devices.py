"""Nuance VCA voice-control stores: the device table and the per-handset phonebooks.

Named for the voice-control component, not a vehicle: the stores sit under Nuance/VCA on
the head unit, and the samples behind this file are Ford SYNC units of two generations.
The NuanceVCAdb/Phone*.sqlite layout found on other units is read by nvcaContacts.py.

    Nuance/VCA/device.sqlite                 table T_Device
    Nuance/VCA/PhoneBook_<address>.sqlite    tables T_Person, T_Phone_Number
"""

import os
import re
import sqlite3

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "nuance_vca_devices": {
        "name": "Nuance VCA - Devices",
        "description": "Rows of the voice-control device table, with the device name and "
                       "Bluetooth address stored in each row and the type, media type and "
                       "status values as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From T_Device in Nuance/VCA/device.sqlite. Tested on three Ford SYNC "
                 "units read from their extracted file sets: a 2019 Ford Fusion (SYNC "
                 "Gen1v5), a 2014 Ford Edge SEL and a 2011 Ford Explorer XLT (SYNC Gen2). "
                 "They held 8, 2 and 10 rows. The table has two layouts. The Gen2 units "
                 "store the Bluetooth address as an integer, shown here as twelve hex "
                 "digits with colons; on the Edge that value equalled the address in the "
                 "name of the unit's call list and phonebook files. The Gen1v5 unit stores "
                 "it as twelve hex digits of text. A zero or empty address is shown empty. "
                 "One handset can have two rows with different Device Type values. Device "
                 "Type, Media Type, Active, Connection Status and Source ID are shown as "
                 "stored because nothing available here documents their values. A row "
                 "records that the voice-control component listed the device. It does not "
                 "establish who carried it.",
        "paths": ('*/Nuance/VCA/device.sqlite*',),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 8 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 2 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 10 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "nuance_vca_phonebook": {
        "name": "Nuance VCA - Handset Phonebook",
        "description": "Contacts in the voice-control phonebook database kept for each "
                       "handset, with the first name, last name, email, phone number and "
                       "the number type text the database stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From T_Person joined to T_Phone_Number and S_Phone_Number_Type in "
                 "Nuance/VCA/PhoneBook_<address>.sqlite. Tested on two Ford SYNC Gen2 units "
                 "read from their extracted file sets, a 2014 Ford Edge SEL and a 2011 Ford "
                 "Explorer XLT, which held one such database each with 47 and 7 numbers. "
                 "The tested SYNC Gen1v5 unit had no PhoneBook database under Nuance/VCA. "
                 "Handset Address is the twelve hex digits in the file name, shown with "
                 "colons. Number Type is the text the database's own type table gives for "
                 "the number. One row is one phone number, so a person with two numbers "
                 "has two rows. The Email column was empty on every tested row. A row "
                 "records that the voice-control component held the "
                 "contact for that handset. It does not establish that any number was "
                 "dialled.",
        "paths": ('*/Nuance/VCA/PhoneBook_*.sqlite*',),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 0 rows, "
                             "no PhoneBook database under Nuance/VCA",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 47 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 7 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_PHONEBOOK_NAME = re.compile(r'PhoneBook_([0-9A-Fa-f]{12})\.sqlite')


def _databases(context, wanted):
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        if not wanted(base) or base.endswith(('-journal', '-wal', '-shm')):
            continue
        try:
            with open(file_found, 'rb') as handle:
                if handle.read(16) != _SQLITE_MAGIC:
                    continue
        except OSError:
            continue
        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        try:
            yield file_found, db
        finally:
            db.close()


def _colons(digits):
    return ':'.join(digits[i:i + 2] for i in range(0, 12, 2)).lower()


def _address(value):
    """A stored Bluetooth address, integer or text, as aa:bb:cc:dd:ee:ff; '' when empty."""
    if isinstance(value, int):
        return _colons(f'{value:012x}') if 0 < value < 2 ** 48 else ''
    text = str(value or '').strip()
    if re.fullmatch(r'[0-9A-Fa-f]{12}', text):
        return _colons(text)
    return text


@artifact_processor
def nuance_vca_devices(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: name.startswith('device.sqlite')):
        try:
            cursor = db.execute('SELECT * FROM T_Device')
            columns = [item[0].lower() for item in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read T_Device: {ex}')
            continue
        source_paths.append(file_found)
        for row in rows:
            address = row.get('btaddress', row.get('bt_address'))
            source_id = row.get('src_id', row.get('device_source_id'))
            data_list.append((
                row.get('device_name') or '', _address(address), row.get('device_type'),
                row.get('media_type'), row.get('active_device'),
                row.get('connection_status'), source_id, row.get('t_device_id'),
                context.get_relative_path(file_found)))

    data_headers = ('Device Name', 'Bluetooth Address', 'Device Type (as stored)',
                    'Media Type (as stored)', 'Active (as stored)',
                    'Connection Status (as stored)', 'Source ID (as stored)', 'Row ID',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def nuance_vca_phonebook(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context,
                                     lambda name: _PHONEBOOK_NAME.match(name) is not None):
        try:
            rows = db.execute('''
                SELECT p.First_Name, p.Last_Name, p.Email, n.Phone_Number,
                       t.Phone_Number_Type
                FROM T_Phone_Number n
                LEFT JOIN T_Person p ON p.T_Person_id = n.T_Person_Id
                LEFT JOIN S_Phone_Number_Type t
                       ON t.S_Phone_Number_Type_id = n.S_Phone_Number_Type_Id
                ORDER BY n.T_Phone_Number_id''').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read the phonebook tables: {ex}')
            continue
        source_paths.append(file_found)
        address = _colons(_PHONEBOOK_NAME.match(os.path.basename(file_found)).group(1))
        for first, last, email, number, number_type in rows:
            data_list.append((address, first or '', last or '', email or '', number or '',
                              number_type or '', context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'First Name', 'Last Name', 'Email', 'Phone Number',
                    'Number Type', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
