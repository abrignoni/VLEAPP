__artifacts_v2__ = {
    "hyundaiDevices": {
        "name": "Hyundai - Bluetooth Paired Devices",
        "description": "Bluetooth device MAC addresses and friendly names from Hyundai/Kia wireless_dev_list.dat.",
        "author": "Nixy Camacho, @pmpulkownik",
        "version": "0.3",
        "creation_date": "2023-06-09",
        "last_update_date": "2026-09-03",
        "requirements": "none",
        "category": "Hyundai Vehicles",
        "notes": "Scans wireless_dev_list.dat for an ASCII MAC address followed by a NUL byte, an "
                 "optional second MAC and a run of printable bytes taken as the friendly name. "
                 "Whether a listed device was paired is not established. A repeated address and "
                 "name pair is listed once. Built from one Hyundai/Kia head unit extraction that "
                 "could not be shared. No row counts are recorded here and no test fixture "
                 "accompanies this artifact. The friendly name runs to the next control byte.",
        "paths": ('*/wireless_dev_list.dat',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    }
}

import re
from scripts.ilapfuncs import artifact_processor

# Matches: MAC address (17 ASCII chars + null), optional repeated MAC, and the friendly
# name. The name runs to the next control byte: the record delimits it the same way it
# delimits the MAC, so a trailing or embedded control byte ends the name rather than
# travelling into the report.
_RECORD_RE = re.compile(
    rb'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\x00'
    rb'(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\x00)?'
    rb'([^\x00-\x1f\x7f]+)'
)


@artifact_processor
def hyundaiDevices(context):
    data_list = []
    source_path = ''

    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found

        try:
            with open(file_found, 'rb') as f:
                content = f.read()

            for match in _RECORD_RE.finditer(content):
                mac_addr = match.group(1).decode('ascii', 'replace').upper()
                raw_name = match.group(2)
                try:
                    dev_name = raw_name.decode('utf-8').strip()
                except UnicodeDecodeError:
                    dev_name = raw_name.decode('latin-1', 'replace').strip()

                if dev_name and (mac_addr, dev_name) not in data_list:
                    data_list.append((mac_addr, dev_name))
        except (OSError, IOError):
            continue

    data_headers = ('Bluetooth MAC Address', 'Device Friendly Name')
    return data_headers, data_list, context.get_relative_path(source_path)
