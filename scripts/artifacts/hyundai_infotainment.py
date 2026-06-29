__artifacts_v2__ = {
    "hyundaiInfotainment": {
        "name": "Hyundai - Infotainment Data",
        "description": "Infotainment/wifi settings (key=value) from a Hyundai wifi/settings file.",
        "author": "Nixy Camacho",
        "version": "0.2",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "",
        "paths": ('*/wifi/settings',),
        "output_types": "standard",
        "artifact_icon": "settings",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def hyundaiInfotainment(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if "[" in line or "]" in line:
                    continue
                splits = line.split("=")
                if len(splits) == 2:
                    data_list.append((splits[0].strip(), splits[1].strip()))

    data_headers = ('ID', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
