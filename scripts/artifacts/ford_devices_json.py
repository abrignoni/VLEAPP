__artifacts_v2__ = {
    "get_devices_json": {
        "name": "Devices from json",
        "description": "Bluetooth devices (MAC, serial, name) from a Ford devices.json.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/devices.json',),
        "output_types": "standard",
        "artifact_icon": "smartphone",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def get_devices_json(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            address = name = serial = ''
            for line in f:
                if '"bluetooth_mac_address": "' in line and address != "":
                    if address and serial and name and (address, serial, name) not in data_list:
                        data_list.append((address, serial, name))
                    name = serial = ''
                    address = line.split('"bluetooth_mac_address": "')[1].strip()[:-2]
                elif '"bluetooth_mac_address": "' in line and address == "":
                    address = line.split('"bluetooth_mac_address": "')[1].strip()[:-2]
                if '"serial_number": "' in line:
                    serial = line.split('"serial_number": "')[1].strip()[:-2]
                if '"device_name": "' in line:
                    name = line.split('"device_name": "')[1].strip()[:-2]
            if address and serial and name and (address, serial, name) not in data_list:
                data_list.append((address, serial, name))

    data_headers = ('Mac Address', 'Serial', 'Name')
    return data_headers, data_list, context.get_relative_path(source_path)
