__artifacts_v2__ = {
    "pasDeGeoDevLoc": {
        "name": "Ford - PAS Dev Loc Results",
        "description": "Device location results (lat/long/alt/heading) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Latitude/Longitude exposed for the KML map.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "pasDeGeoSpeed": {
        "name": "Ford - PAS Road Speed Limits",
        "description": "Road speed limits from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "alert-triangle",
    },
    "pasDeGeoApInfo": {
        "name": "Ford - PAS Access Point List",
        "description": "Wi-Fi access points (BSSID/SSID/signal) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "wifi",
    },
    "pasDeGeoVSpeed": {
        "name": "Ford - PAS Vehicle Speed",
        "description": "Vehicle speed readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "navigation",
    },
    "pasDeGeoTransm": {
        "name": "Ford - PAS Transmission Status",
        "description": "Transmission status readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "settings",
    },
    "pasDeGeoTemp": {
        "name": "Ford - PAS Outside Temperature",
        "description": "Outside air temperature readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "pasDeGeoOdometer": {
        "name": "Ford - PAS Odometer",
        "description": "Odometer readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "activity",
    },
    "pasDeGeoVehicle": {
        "name": "Ford - PAS Vehicle Info",
        "description": "Vehicle identity (VIN/make/model/platform) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.2", "creation_date": "2021-07-08",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Surfaces the make/model/VIN/platform the original only wrote to the device-info "
                 "log.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "truck",
    },
}

import os
import re
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logdevinfo

_NUM = r"([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?"
_RE = {k: re.compile(f"({label} {_NUM})") for k, label in (
    ('lon1', 'Longitude = '), ('lat1', 'Latitude ='), ('alt1', 'Altitude ='),
    ('lon2', 'Lon = '), ('lat2', 'Lat ='), ('alt2', 'Alt ='), ('head', 'Heading ='))}


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


def _val(match):
    return match[2] if match else ''


def _parse(context):
    sect = {k: [] for k in ('dev', 'speed', 'apinfo', 'vspeed', 'transm', 'outtemp', 'odometer',
                            'vehicle')}
    vins, platforms, make, model = [], [], '', ''
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        basename = os.path.basename(file_found)
        bssid, ts_link = '', ''
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                try:
                    if 'NAV_FRAMEWORK_IF' in line and 'dev_loc_results' in line \
                            and 'ERROR  RPT!!!' not in line:
                        if 'Longitude =' in line:
                            lat, lon, alt = _RE['lat1'].search(line), _RE['lon1'].search(line), \
                                _RE['alt1'].search(line)
                        elif 'Lon =' in line:
                            lat, lon, alt = _RE['lat2'].search(line), _RE['lon2'].search(line), \
                                _RE['alt2'].search(line)
                        else:
                            lat = lon = alt = None
                        if lat and lon:
                            sect['dev'].append((_ts(timeorder(line)), _val(lat), _val(lon),
                                                _val(alt), _val(_RE['head'].search(line)),
                                                'NAV_FRAMEWORK_IF', 'dev_loc_results', basename))
                    if 'Speed limit' in line:
                        parts = line.split(',')
                        street = parts[-2].split(':')[-1].replace('[', '').replace(']', '').strip()
                        limit = parts[-1].split(':')[-1].replace('[', '').replace(']', '').strip()
                        if street:
                            sect['speed'].append((_ts(timeorder(line)), street, limit, basename))
                    if 'WIFI_MID' in line:
                        if 'Extracted BSSID' in line:
                            bssid = line.split('=')[-1].strip()
                        if 'SSID:' in line:
                            parts = line.split(';')
                            ssid = parts[0].split(':')[-1].strip()
                            signal = parts[-1].split(',')[-1].split(':')[-1].strip()
                            sect['apinfo'].append((_ts(timeorder(line)), bssid, ssid, signal,
                                                   basename))
                    if 'QT_HMI' in line:
                        last = line.strip().split(' ')[-1].replace('"', '').strip()
                        if 'VehicleSpeed' in line:
                            sect['vspeed'].append((_ts(timeorder(line)), last, basename))
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
def pasDeGeoDevLoc(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Altitude Ft', 'Heading',
               'Category', 'Subcategory', 'Log Filename')
    return headers, sect['dev'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Road', 'Speed Limit', 'Log Filename')
    return headers, sect['speed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoApInfo(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'BSSID', 'SSID', 'Signal Strength', 'Log Filename')
    return headers, sect['apinfo'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoVSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Vehicle Speed', 'Log Filename')
    return headers, sect['vspeed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTransm(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Transmission Status', 'Log Filename')
    return headers, sect['transm'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTemp(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Temperature', 'Log Filename')
    return headers, sect['outtemp'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoOdometer(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Odometer', 'Log Filename')
    return headers, sect['odometer'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoVehicle(context):
    sect, source_path = _parse(context)
    for field, value in sect['vehicle']:
        logdevinfo(f"{field} from pas_debug: {value}")
    return ('Field', 'Value'), sect['vehicle'], context.get_relative_path(source_path)
