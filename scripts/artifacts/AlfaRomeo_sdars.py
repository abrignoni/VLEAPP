__artifacts_v2__ = {
    "alfaRomeoSirius": {
        "name": "Alfa Romeo - Sirius Settings",
        "description": "SiriusXM (SDARS) settings/values from an Alfa Romeo sdars_db.sqlite.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2023-06-16",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Alfa Romeo Vehicles",
        "notes": "",
        "paths": ('*/sdars_db.sqlite*',),
        "output_types": "standard",
        "artifact_icon": "radio",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def alfaRomeoSirius(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('sdars_db.sqlite'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT siriusdata.value_name, siriusdata.value_description, siriusdata.value_string
            FROM siriusdata
        ''')
        for row in cursor.fetchall():
            data_list.append((row[0], row[1], row[2]))
        db.close()

    data_headers = ('Name', 'Description', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
