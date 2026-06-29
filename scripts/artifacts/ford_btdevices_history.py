__artifacts_v2__ = {
    "BT_Device_History": {
        "name": "BT Device History",
        "description": "Bluetooth connect/disconnect history from a Ford smartdevicelink.log.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Time is parsed from the log's [DD Mon YYYY HH:MM:SS...] stamp and normalized to "
                 "UTC; unparseable values are kept as stored.",
        "paths": ('*/*smartdevicelink.log',),
        "output_types": "standard",
        "artifact_icon": "bluetooth",
        "function": "get_bt_device_hist",
    }
}

from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor


def get_time(line):
    desired_part = line.split("]")[0]
    date = desired_part.split("[")[1].split(" ")
    day, month, year = date[0], date[1], date[2]
    time = date[3][0:-4]
    return f"{year}-{month}-{day} {time}"


def _ts(value):
    value = (value or '').strip()
    if not value:
        return value
    for fmt in ('%Y-%b-%d %H:%M:%S', '%Y-%B-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        return value


@artifact_processor
def get_bt_device_hist(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if "appeared: Device name: " not in line:
                    continue
                splits = line.split("appeared: Device name: ")
                timestamp = get_time(line)
                name = splits[1].strip()
                incoming = "Device Disconnected" if splits[0][-3:] == "dis" else "Device Connected"
                serial = next(f, '').split("Device serial: ")[-1].strip()
                uuid = next(f, '').split("Device uuid: ")[-1].strip()
                connection_type = next(f, '').split("Device type: ")[-1].strip()
                row = (_ts(timestamp), serial, name, uuid, connection_type, incoming)
                if name and serial and uuid and connection_type and row not in data_list:
                    data_list.append(row)

    data_headers = (('Time', 'datetime'), 'Serial', 'Name', 'uuid', 'Connection Type',
                    'Incoming/Outgoing')
    return data_headers, data_list, context.get_relative_path(source_path)
