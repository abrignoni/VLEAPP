__artifacts_v2__ = {
    "chryslerAccessories": {
        "name": "Chrysler - Accessory Data",
        "description": "Accessory data (name::value pairs) from a Chrysler media/accessory_data.txt.",
        "author": "Joe Dinsmoor",
        "version": "0.2",
        "creation_date": "2023-06-08",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/media/accessory_data.txt',),
        "output_types": "standard",
        "artifact_icon": "sliders",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def chryslerAccessories(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                names = line.split("::")
                if len(names) < 2:
                    continue
                data_list.append((names[0].strip(), names[1].strip()))

    data_headers = ('Name', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
