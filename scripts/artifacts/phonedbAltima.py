__artifacts_v2__ = {
    "phoneBookAltima": {
        "name": "Nissan - Phone Book Contacts",
        "description": "Phonebook contacts (per paired device) from a Nissan Altima "
                       "ffs/phone_db.db.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2023-02-14",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Nissan Vehicles",
        "notes": "The DB holds one phonebook per paired device (NUM_PHONEBOOK_<n>/phonebook_<n>); "
                 "the original emitted one report per phonebook, here flattened into a single "
                 "table with a Phone Book column. Phone Number/s is a '; '-joined list.",
        "paths": ('*/ffs/phone_db.db*',),
        "output_types": "standard",
        "artifact_icon": "book",
    }
}

import sqlite3

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def phoneBookAltima(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('phone_db.db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute("SELECT NAME FROM SQLITE_SCHEMA WHERE NAME LIKE 'NUM_PHONEBOOK%' "
                       "ORDER BY name")
        for (tablename,) in cursor.fetchall():
            num = tablename.split('_')[2]
            try:
                cursor.execute(f'''
                    SELECT num_phonebook_{num}.entry_id, phonebook_{num}.first_name,
                           phonebook_{num}.last_name,
                           GROUP_CONCAT(num_phonebook_{num}.number, '; ')
                    FROM num_phonebook_{num}
                    JOIN phonebook_{num}
                      ON num_phonebook_{num}.entry_id = phonebook_{num}.entry_id
                    GROUP BY num_phonebook_{num}.entry_id
                ''')
            except sqlite3.Error:
                continue
            for row in cursor.fetchall():
                data_list.append((num, row[0], row[1], row[2], row[3]))
        db.close()

    data_headers = ('Phone Book', 'ID', 'First Name', 'Last Name', 'Phone Number/s')
    return data_headers, data_list, context.get_relative_path(source_path)
