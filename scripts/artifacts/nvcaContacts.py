__artifacts_v2__ = {
    "nvcaContacts": {
        "name": "Nuance VCA - Contacts",
        "description": "Contacts with phone numbers from a Nuance VCA phone database "
                       "(NuanceVCAdb/Phone*.sqlite).",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2021-07-15",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "",
        "paths": ('*/Nuance/NuanceVCAdb/Phone*.sqlite*',),
        "output_types": "standard",
        "artifact_icon": "user",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def nvcaContacts(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.sqlite'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT First_Name, Last_Name, Phone_Number, Phone_Number_Type
            FROM S_Phone_Number_Type, t_phone_number
            WHERE S_Phone_Number_Type.S_Phone_Number_Type_id = t_phone_number.S_Phone_Number_Type_Id
        ''')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2], row[3]))
        db.close()

    data_headers = ('First Name', 'Last Name', ('Phone Number', 'phonenumber'), 'Type')
    return data_headers, data_list, context.get_relative_path(source_path)
