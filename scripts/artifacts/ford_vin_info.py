__artifacts_v2__ = {
    "Vin_Number": {
        "name": "VIN",
        "description": "Vehicle Identification Number(s) from a Ford vin.txt.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Original only wrote the VIN to the device-info log; it is now also surfaced as a "
                 "table.",
        "paths": ('*/vin.txt',),
        "output_types": "standard",
        "artifact_icon": "hash",
        "function": "get_info",
    }
}

from scripts.ilapfuncs import artifact_processor, logdevinfo


@artifact_processor
def get_info(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                vin = line.strip()
                if vin and (vin,) not in data_list:
                    data_list.append((vin,))
                    logdevinfo(f"VIN from Vin.txt: {vin}")

    data_headers = ('VIN',)
    return data_headers, data_list, context.get_relative_path(source_path)
