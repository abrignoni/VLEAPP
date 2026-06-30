__artifacts_v2__ = {
    "hyundaiTelematicsGps": {
        "name": "Hyundai - Telematics GPS Detail",
        "description": "GPS Detail parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "hyundaiTelematicsWdw": {
        "name": "Hyundai - Telematics WdwStatus",
        "description": "WdwStatus parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "hyundaiTelematicsWeather": {
        "name": "Hyundai - Telematics Weather Waypoint",
        "description": "Weather waypoints parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": "standard", "artifact_icon": "cloud",
    },
    "hyundaiTelematicsEngineIdle": {
        "name": "Hyundai - Telematics Engine Idle Alarm",
        "description": "Engine idle alarm events parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": "standard", "artifact_icon": "alert-circle",
    },
    "hyundaiTelematicsDriving": {
        "name": "Hyundai - Telematics Driving Events",
        "description": "Driving events parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": "standard", "artifact_icon": "navigation",
    },
    "hyundaiTelematicsCan": {
        "name": "Hyundai - Telematics CAN Events",
        "description": "CAN bus events parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": "standard", "artifact_icon": "cpu",
    },
    "hyundaiTelematicsProvisioning": {
        "name": "Hyundai - Telematics Provisioning",
        "description": "Provisioning records (VIN/MDM/MIN) parsed from a Hyundai telematics.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2023-02-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Hyundai Vehicles",
        "notes": "", "paths": ('*/telematics.log*',),
        "output_types": "standard", "artifact_icon": "key",
    },
}

import os
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor


def _ts(value):
    value = (value or '').strip()
    if not value:
        return value
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        return value


def _parse(context):
    sections = {'gps': [], 'wdw': [], 'weather': [], 'engine': [], 'driving': [], 'can': [],
                'prov': []}
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        filename = os.path.basename(file_found)
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if line.startswith(' <Boot'):
                    continue
                line = line.rstrip('\n')
                parts = line.split(' ', 2)
                if len(parts) < 2:
                    continue
                timestamp = f"XXXX-{parts[0]} {parts[1]}"
                try:
                    if 'initLastGpsDetail' in line:
                        s = line.split(' ')
                        speed = s[18].split('Speed:')[1]
                        head = s[18].split('Speed:')[0].split('Head:')[1]
                        latitude = s[15]
                        longitude = s[16].split(':')[1]
                        offset = s[20].split(':')[1]
                        t = s[19].split(':')[1]
                        fecha = f'{t[0:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}'
                        sections['gps'].append((timestamp, _ts(fecha), offset, latitude, longitude,
                                                head, speed, filename))
                    elif 'wdwStatus' in line:
                        s = line.split(' ')
                        sections['wdw'].append((timestamp, s[13], s[16].split()[4],
                                                s[16].split()[5]))
                    elif 'Address_name' in line:
                        addr = line.split('Address_name :')[1].split(',', 2)
                        sections['weather'].append((timestamp, f'{addr[0]} {addr[1]}'))
                    elif 'EngineIdleAlarmTask' in line:
                        sections['engine'].append((timestamp,
                                                   line.split('[EngineIdleAlarmTask] ')[1].strip()))
                    elif '[DRIVING] ' in line:
                        sections['driving'].append((timestamp, line.split('[DRIVING]')[1].strip()))
                    elif '[Provisioning]' in line:
                        e = line.split(' ')
                        sections['prov'].append((timestamp, e[15].split(':')[1],
                                                 e[16].split(':')[1], e[17].split(':')[1]))
                    elif '[CAN]' in line:
                        sections['can'].append((timestamp, line.split('[CAN]')[1].strip()))
                except (IndexError, ValueError):
                    continue
    return sections, source_path


@artifact_processor
def hyundaiTelematicsGps(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', ('Date', 'datetime'), 'Date Offset', 'Latitude', 'Longitude',
                    'Head', 'Speed', 'Source')
    return data_headers, sections['gps'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsWdw(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'Descriptor', 'Latitude', 'Longitude')
    return data_headers, sections['wdw'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsWeather(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'Address')
    return data_headers, sections['weather'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsEngineIdle(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'Events')
    return data_headers, sections['engine'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsDriving(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'Events')
    return data_headers, sections['driving'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsCan(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'Events')
    return data_headers, sections['can'], context.get_relative_path(source_path)


@artifact_processor
def hyundaiTelematicsProvisioning(context):
    sections, source_path = _parse(context)
    data_headers = ('Timestamp', 'VIN', 'MDM', 'MIN')
    return data_headers, sections['prov'], context.get_relative_path(source_path)
