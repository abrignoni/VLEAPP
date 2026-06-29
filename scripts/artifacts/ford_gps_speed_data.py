__artifacts_v2__ = {
    "GPS_Speed_Data": {
        "name": "GPS Speed Data",
        "description": "Dead-reckoning speed/heading data from Ford fdp logs.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Time Stamp normalized to UTC where parseable; unparseable values kept as stored. "
                 "(These records carry speed/heading but no latitude/longitude, so there is no map.)",
        "paths": ('*/*fdplog.np.txt*',),
        "output_types": "standard",
        "artifact_icon": "navigation",
        "function": "get_ford_gps_speed_data",
    }
}

from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor

_TID = '[fdp@30513 tid="7"]'


def _ts(value):
    value = (value or '').strip()
    if not value:
        return value
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M:%S'):
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
def get_ford_gps_speed_data(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                if f'{_TID} DR data:' not in line or "GPSDataValid=1" not in line:
                    continue
                splits1 = line.split(f'{_TID} DR data:')[1].strip()
                nxt = next(f, None)
                while nxt is not None and _TID not in nxt:
                    nxt = next(f, None)
                if nxt is None:
                    break
                splits2 = nxt.split(f'{_TID} ')[1].strip()
                full_line = splits1 + (" " + splits2 if splits2[:1] == "S" else splits2)
                lineparts = full_line.split(" ")
                try:
                    timestamp = lineparts[4] + " " + lineparts[5]
                    heading = lineparts[9].split("Heading=")[1]
                    compass_dir = lineparts[12].split("compDir=")[1]
                    speed = lineparts[13].split("Speed=")[1]
                except (IndexError, ValueError):
                    continue
                row = (_ts(timestamp), speed, heading, compass_dir)
                if speed and heading and compass_dir and row not in data_list:
                    data_list.append(row)

    data_headers = (('Time Stamp', 'datetime'), 'Speed', 'Heading', 'Compass Direction')
    return data_headers, data_list, context.get_relative_path(source_path)
