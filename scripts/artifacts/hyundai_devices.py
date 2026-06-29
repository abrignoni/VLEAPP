__artifacts_v2__ = {
    "hyundaiDevices": {
        "name": "Hyundai - Bluetooth Devices",
        "description": "Bluetooth device MAC addresses and friendly names from a Hyundai "
                       "wireless_dev_list.dat.",
        "author": "Nixy Camacho",
        "version": "0.2",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "",
        "paths": ('*/wireless_dev_list.dat',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    }
}

import re

from scripts.ilapfuncs import artifact_processor

_ADDR_RE = re.compile(r"[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:[A-Za-z0-9]+:"
                      r"[A-Za-z0-9]+", re.IGNORECASE)


@artifact_processor
def hyundaiDevices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        dev_addr, dev_name = [], []
        with open(file_found, 'r', encoding='latin-1') as f:
            for line in f:
                text_only = _ADDR_RE.sub('~~~', line).split('~~~')
                if len(text_only) == 1:
                    name = text_only[0].strip().strip('\x00').strip('\x01').strip('\x02')
                    if name and name not in dev_name:
                        dev_name.append(name)
                addrs = _ADDR_RE.findall(line)
                if len(addrs) == 1 and addrs[0] not in dev_addr:
                    dev_addr.append(addrs[0])
        data_list.extend(zip(dev_addr, dev_name))

    data_headers = ('Bluetooth MAC Address', 'Device Friendly Name')
    return data_headers, data_list, context.get_relative_path(source_path)
