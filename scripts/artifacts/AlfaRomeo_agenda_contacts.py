__artifacts_v2__ = {
    "alfaRomeoContacts": {
        "name": "Alfa Romeo - Contacts",
        "description": "Contacts (with phone numbers and paired BT device) from an Alfa Romeo "
                       "agenda.sqlite.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2023-06-16",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Alfa Romeo Vehicles",
        "notes": "",
        "paths": ('*/agenda.sqlite*',),
        "output_types": "standard",
        "artifact_icon": "user",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def alfaRomeoContacts(context):
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
            SELECT ContactCard.FIRSTNAME, ContactCard.SURNAME, PhoneNumber.NUMBER,
                   BT_Device.BD_ADDRESS
            FROM ContactCard
            LEFT JOIN BT_Device ON ContactCard.BT_DEVICE_ID = BT_Device.ID
            LEFT JOIN PhoneNumber ON ContactCard.ID = PhoneNumber.CONTACT_ID
        ''')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2], row[3]))
        db.close()

    data_headers = ('First Name', 'Last Name', ('Phone Number', 'phonenumber'), 'BT Address')
    return data_headers, data_list, context.get_relative_path(source_path)
