__artifacts_v2__ = {
    "mediaService": {
        "name": "Ford - Media Service",
        "description": "Connected media-store devices from a Ford SYNC mediaservice_db.",
        "author": "gforce4n6",
        "version": "0.2",
        "creation_date": "2024-03-28",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/mediaservice_db*',),
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    }
}

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


@artifact_processor
def mediaService(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('mediaservice_db'):
            continue
        source_path = file_found
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()
        cursor.execute('''
            SELECT mediastores.btdeviceid, mediastores.serial, mediastores.device_id,
                   mediastores.manufacturer, mediastores.product, mediastores.device_name,
                   mediastores.vendorid, mediastores.productid,
                   CASE mediastores.attached WHEN '0' THEN 'No' WHEN '1' THEN 'Yes'
                        ELSE 'Not Specified' END,
                   CASE mediastores.active_onshutdown WHEN '0' THEN 'No' WHEN '1' THEN 'Yes'
                        ELSE 'Not Specified' END,
                   CASE mediastores.remote WHEN '0' THEN 'No' WHEN '1' THEN 'Yes'
                        ELSE 'Not Specified' END,
                   mediastores.fs_type
            FROM mediastores
            ORDER BY mediastores.btdeviceid
        ''')
        for row in cursor.fetchall():
            data_list.append(tuple(row))
        db.close()

    data_headers = ('BT Device ID', 'Serial', 'Device ID', 'Manufacturer', 'Product',
                    'Device Name', 'Vendor ID', 'Product ID', 'Device Attached',
                    'Active on Shutdown', 'Is Remote', 'FS Type')
    return data_headers, data_list, context.get_relative_path(source_path)
