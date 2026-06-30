__artifacts_v2__ = {
    "dipoAudio": {
        "name": "Hyundai - Dipo Audio UUIDs",
        "description": "Audio app preference UUIDs (incl. local BT address) from a Hyundai Santa Fe "
                       "com.daudio.app.dipo pref_dipo.xml.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "",
        "paths": ('*/com.daudio.app.dipo/shared_prefs/pref_dipo.xml',),
        "output_types": "standard",
        "artifact_icon": "music",
    }
}

import xml.etree.ElementTree as ET

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def dipoAudio(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        root = ET.parse(file_found).getroot()
        for elem in root:
            name = elem.attrib.get('name', '')
            text = elem.text if name == 'pref_key_local_bt_address' else ''
            data_list.append((name, text))

    data_headers = ('UUID', 'Extra Value')
    return data_headers, data_list, context.get_relative_path(source_path)
