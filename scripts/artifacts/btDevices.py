__artifacts_v2__ = {
    "btDevices": {
        "name": "Bluetooth Devices",
        "description": "Bluetooth device details from Ford SYNC devlog text logs (BT/devlog_*.txt).",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2021-07-02",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Bluetooth",
        "notes": "",
        "paths": ('*/BT/devlog_*.txt',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def btDevices(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        devaddval = manuval = devmodval = supprofval = phonedownval = ''
        availcodecval = servsupval = subscribenumval = netnameval = ''
        devsoftval = devfriendval = classdevval = chldval = inbandval = brsfval = ''
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                splits = line.split(':', 1)
                if len(splits) > 1:
                    key = splits[0].strip()
                    value = splits[1].strip()
                    if key == 'Device Address':
                        devaddval = value
                    if key == 'Manufacturer':
                        manuval = value.strip('"')
                    if key == 'Device Model':
                        devmodval = value
                    if key == 'SupportedProfiles':
                        supprofval = value
                    if key == 'Phonebook Download Support':
                        phonedownval = value
                    if key == 'Available Codec':
                        availcodecval = value
                    if key == 'Service Supported':
                        servsupval = value
                    if key == 'subscriberNum':
                        subscribenumval = value
                    if key == 'networkName':
                        netnameval = value
                    if key == 'deviceSoftwareVersion':
                        devsoftval = value
                    if key == 'Device Friendly Name':
                        devfriendval = value
                    if key == 'Class Of Device':
                        classdevval = value
                    if key == 'CHLD capabilities':
                        chldval = value
                else:
                    if 'BRSF' in splits[0]:
                        brsfval = splits[0].strip()
                    if 'CHLD' in splits[0]:
                        chldval = splits[0].split('=')[1].strip()
                    if 'In-Band' in splits[0]:
                        inbandval = splits[0].strip()
                    if 'Phonebook' in splits[0]:
                        phonedownval = splits[0].strip()
        data_list.append((devmodval, manuval, subscribenumval, devfriendval, devaddval, devsoftval,
                          netnameval, supprofval, classdevval, servsupval, availcodecval,
                          phonedownval, chldval, brsfval, inbandval))

    data_headers = ('Device Model', 'Manufacturer', 'Subscriber Number', 'Device Friendly Name',
                    'Device Address', 'Device Software Version', 'Network Name',
                    'Supported Profiles', 'Class of Device', 'Service Supported', 'Available Codec',
                    'Phonebook Download Support', 'CHLD Capabilities', 'BRSF', 'In-Band')
    return data_headers, data_list, context.get_relative_path(source_path)
