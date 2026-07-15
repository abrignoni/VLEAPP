__artifacts_v2__ = {
    "get_Model": {
        "name": "Vehicle Model",
        "description": "Vehicle/head-unit model from a Ford bluetooth_v1.ddb.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Original only wrote the model to the device-info log; it is now also surfaced as a "
                 "table.",
        "paths": ('*/bluetooth_v1.ddb',),
        "output_types": "standard",
        "artifact_icon": "truck",
    }
}

from scripts.ilapfuncs import artifact_processor, logdevinfo


@artifact_processor
def get_Model(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                if "device_name" not in line:
                    continue
                value_line = next(f, '')
                if "<Value>" not in value_line:
                    continue
                model = value_line.split("<Value>")[1].split("<")[0].strip()
                if model and (model,) not in data_list:
                    data_list.append((model,))
                    logdevinfo(f"Model from Bluetooth_v1.ddb: {model}")

    data_headers = ('Vehicle Model',)
    return data_headers, data_list, context.get_relative_path(source_path)
