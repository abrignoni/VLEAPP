__artifacts_v2__ = {
    "phoneConfigAltima": {
        "name": "Nissan - Phone Config",
        "description": "Phone configuration (INI-style key/value sections) from a Nissan Altima "
                       "ffs/phone_config.dat.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2023-02-13",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Nissan Vehicles",
        "notes": "Sections are reported in one table with a Section column. Underscores in section "
                 "names are shown as spaces, and keys with an empty value are not listed.",
        "paths": ('*/ffs/phone_config.dat',),
        "output_types": "standard",
        "artifact_icon": "settings",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def phoneConfigAltima(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        section = ''
        with open(file_found, 'r', encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if '[' in line:
                    section = line.replace('[', '').replace(']', '').replace('_', ' ').strip()
                elif '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip()
                    if value:
                        data_list.append((section, key.strip(), value))

    data_headers = ('Section', 'Key', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
