__artifacts_v2__ = {
    "chryslerBtDevices": {
        "name": "Chrysler - Bluetooth Devices",
        "description": "Paired Bluetooth devices (address + friendly name) from a Chrysler "
                       "betula/bt_log.txt.",
        "author": "Joe Dinsmoor",
        "version": "0.2",
        "creation_date": "2023-06-02",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/betula/bt_log.txt',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def chryslerBtDevices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if 'bdAddr: ' not in line:
                    continue
                dev_addr = line.split('bdAddr: ')[1].strip()
                next(f, '')
                name_line = next(f, '')
                dev_name = name_line.split('name: ')[1].strip() if 'name: ' in name_line else ''
                if dev_addr and (dev_addr, dev_name) not in data_list:
                    data_list.append((dev_addr, dev_name))

    data_headers = ('Device Address', 'Device Friendly Name')
    return data_headers, data_list, context.get_relative_path(source_path)
