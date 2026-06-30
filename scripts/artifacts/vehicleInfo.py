__artifacts_v2__ = {
    "vehicleInfo": {
        "name": "Ford - Vehicle Info",
        "description": "Vehicle info (name::value pairs: VIN, odometer, fuel level, etc.) from a "
                       "Ford SYNC ppsp reconn/vehicle file.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2021-07-06",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/ppsp/services/reconn/vehicle',),
        "output_types": "standard",
        "artifact_icon": "truck",
    }
}

from scripts.ilapfuncs import artifact_processor, logdevinfo

_DEVINFO = {'fuellevel': 'Fuel Level', 'ignitionstate': 'Ignition State', 'navigation': 'Navigation',
            'odometer': 'Odometer', 'platform': 'Platform', 'vin': 'VIN from PPSP',
            'vmcufpn': 'Firmware'}


@artifact_processor
def vehicleInfo(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                splits = line.split('::')
                if len(splits) < 2 or 'DE0' in splits[0]:
                    continue
                key = splits[0].strip()
                value = splits[1].strip()
                data_list.append((key, value))
                if key in _DEVINFO:
                    logdevinfo(f"{_DEVINFO[key]}: {value}")

    data_headers = ('Key', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
