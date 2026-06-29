__artifacts_v2__ = {
    "hyundaiContacts": {
        "name": "Hyundai - Contacts",
        "description": "Bluetooth contacts from a Hyundai infotainment MC_*.db.",
        "author": "Nixy Camacho",
        "version": "0.2",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Rewritten as a single query (the original ran separate SELECTs and crashed on "
                 "os.path.splittext).",
        "paths": ('*/bluetooth/DB_BMS/MC_*.db*',),
        "output_types": "standard",
        "artifact_icon": "user",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def hyundaiContacts(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('SELECT _id, given_name, family_name, phone_number FROM bluetooth_contacts')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2], row[3]))
        db.close()

    data_headers = ('ID', 'given_name', 'family_name', ('phone_number', 'phonenumber'))
    return data_headers, data_list, context.get_relative_path(source_path)
