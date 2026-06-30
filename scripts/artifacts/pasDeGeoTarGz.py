__artifacts_v2__ = {
    "pasDeGeoTarGzGps": {
        "name": "RAM - PAS GPS Locations",
        "description": "GPS locations from a RAM pas_debug.log.1 inside an archivedata tar.gz.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "Latitude/Longitude exposed for the KML map. The log is read in-memory from the "
                 "tar.gz (the original extracted it to the report folder).",
        "paths": ('*/archivedata/*.tar.gz',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "pasDeGeoTarGzSpeed": {
        "name": "RAM - PAS Road Speed Limits",
        "description": "Road speed limits from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "alert-triangle",
    },
    "pasDeGeoTarGzApInfo": {
        "name": "RAM - PAS Access Point List",
        "description": "Wi-Fi access points from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "wifi",
    },
    "pasDeGeoTarGzVSpeed": {
        "name": "RAM - PAS Vehicle Speed",
        "description": "Vehicle speed (kmph) from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "navigation",
    },
    "pasDeGeoTarGzTransm": {
        "name": "RAM - PAS Transmission Status",
        "description": "Transmission status from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "settings",
    },
    "pasDeGeoTarGzTemp": {
        "name": "RAM - PAS Outside Temperature",
        "description": "Outside air temperature from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "pasDeGeoTarGzOdometer": {
        "name": "RAM - PAS Odometer",
        "description": "Odometer readings from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "activity",
    },
    "pasDeGeoTarGzCurRoad": {
        "name": "RAM - PAS Current Road",
        "description": "Current road from a RAM pas_debug.log.1 (tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "map",
    },
    "pasDeGeoTarGzVehicle": {
        "name": "RAM - PAS Vehicle Info",
        "description": "Vehicle identity (VIN/make/model/platform) from a RAM pas_debug.log.1 "
                       "(tar.gz).",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2024-04-05",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "RAM Vehicles",
        "notes": "Surfaces the make/model/VIN/platform the original only wrote to the "
                 "device-info log.", "paths": ('*/archivedata/*.tar.gz',),
        "output_types": "standard", "artifact_icon": "truck",
    },
}

import os
import tarfile
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logdevinfo


def timeorder(line):
    month, day, yeartime = line.split('/', 3)[0], line.split('/', 3)[1], line.split('/', 3)[2]
    year, time = yeartime.split(' ')[0], yeartime.split(' ')[1]
    return f'{year}-{month}-{day} {time}'


def _ts(value):
    value = (value or '').strip()
    if not value:
        return value
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return value


def _parse(context):
    sect = {k: [] for k in ('dev', 'speed', 'apinfo', 'vspeed', 'transm', 'outtemp', 'odometer',
                            'curroad', 'vehicle')}
    vins, platforms, make, model = [], [], '', ''
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.tar.gz') or os.stat(file_found).st_size == 0:
            continue
        source_path = file_found
        basename = os.path.basename(file_found)
        try:
            with tarfile.open(file_found, 'r') as tar:
                member = tar.extractfile('pas_debug.log.1')
                content = member.read().decode('cp437', errors='backslashreplace') if member else ''
        except (KeyError, tarfile.TarError):
            continue
        bssid, ts_link = '', ''
        for line in content.splitlines():
            try:
                if ': lat: ' in line and 'lon:' in line:
                    parts = line.split(': lat: ')[1].split(',')
                    latitude = parts[0].strip()
                    longitude = parts[1].split('lon: ')[1].strip()
                    heading = parts[2].split('heading: ')[1].strip()
                    sect['dev'].append((_ts(timeorder(line)), latitude, longitude, heading,
                                        basename))
                if '= Speed Limit:' in line and 'Speed limit invalid' not in line:
                    sect['speed'].append((_ts(timeorder(line)), '', line.split('=')[1].strip(),
                                          basename))
                if 'WIFI_MID' in line:
                    if 'Extracted BSSID' in line:
                        bssid = line.split('=')[-1].strip()
                    if 'SSID:' in line:
                        parts = line.split(';')
                        ssid = parts[0].split(':')[-1].strip()
                        signal = parts[-1].split(',')[-1].split(':')[-1].strip()
                        sect['apinfo'].append((_ts(timeorder(line)), bssid, ssid, signal, basename))
                if '] currentRoad' in line and 'nv_navigation' in line:
                    road = line.split('] [')[-1].split('] currentRoad')[0]
                    sect['curroad'].append((_ts(timeorder(line)), road, basename))
                if '[SAL_SWITCH_DISPLAY] Received speed:' in line:
                    speeds = line.split('[SAL_SWITCH_DISPLAY] Received speed:')[1].strip()
                    sect['vspeed'].append((_ts(timeorder(line)), speeds.split(' kmph')[0]))
                if 'QT_HMI' in line:
                    last = line.strip().split(' ')[-1].replace('"', '').strip()
                    if 'TransmissionStatus' in line:
                        sect['transm'].append((_ts(timeorder(line)), last, basename))
                    if 'General_Temperature_Unit_INT' in line:
                        sect['outtemp'].append((_ts(timeorder(line)), f'Temp. Unit: {last}',
                                                basename))
                    if 'OutsideAirTemperature_E_FLT' in line:
                        sect['outtemp'].append((_ts(timeorder(line)), last, basename))
                if 'USBUPDT_MID' in line and '=Line read is Version Number =' in line:
                    ver = line.strip().split('=')[-1].strip()
                    if ver and ver not in platforms:
                        platforms.append(ver)
                if 'CAppLinkService' in line:
                    ts_link = _ts(timeorder(line))
                if 'odometer' in line:
                    sect['odometer'].append((ts_link, line.strip().split(':')[-1].strip(),
                                             basename))
                if '"vin" :' in line:
                    vin = line.strip().split(':')[-1].strip().replace('"', '')
                    if vin and vin not in vins:
                        vins.append(vin)
                if 'VIN got from GGC' in line:
                    vin = line.strip().split('=')[-1].strip()
                    if vin and vin not in vins:
                        vins.append(vin)
                if '"make"' in line:
                    make = line.strip().split(':')[-1].strip().replace('"', '')
                if '"model"' in line:
                    model = line.strip().split(':')[-1].strip().replace('"', '')
            except (IndexError, ValueError, TypeError):
                continue

    if make:
        sect['vehicle'].append(('Make', make))
    if model:
        sect['vehicle'].append(('Model', model))
    for vin in vins:
        sect['vehicle'].append(('VIN', vin))
    for pver in platforms:
        sect['vehicle'].append(('Platform Version', pver))
    return sect, source_path


@artifact_processor
def pasDeGeoTarGzGps(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Heading', 'Log Filename')
    return headers, sect['dev'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Road', 'Speed Limit', 'Log Filename')
    return headers, sect['speed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzApInfo(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'BSSID', 'SSID', 'Signal Strength', 'Log Filename')
    return headers, sect['apinfo'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzVSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Vehicle Speed KMPH')
    return headers, sect['vspeed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzTransm(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Transmission Status', 'Log Filename')
    return headers, sect['transm'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzTemp(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Temperature', 'Log Filename')
    return headers, sect['outtemp'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzOdometer(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Odometer', 'Log Filename')
    return headers, sect['odometer'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzCurRoad(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Current Road', 'Log Filename')
    return headers, sect['curroad'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTarGzVehicle(context):
    sect, source_path = _parse(context)
    for field, value in sect['vehicle']:
        logdevinfo(f"{field} from pas_debug tar.gz: {value}")
    return ('Field', 'Value'), sect['vehicle'], context.get_relative_path(source_path)
