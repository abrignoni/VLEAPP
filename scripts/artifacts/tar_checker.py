__artifacts_v2__ = {
    "chryslerTarGps": {
        "name": "Chrysler - Tar GZ GPS Locations",
        "description": "Latitude, longitude and heading from lines carrying \"lat:\", "
                       "\"lon:\" and \"heading:\" in a pas_debug log inside a Chrysler "
                       "[H-M]_*.tar.gz archive.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude exposed for the KML map. The log is read in memory from "
                 "the tar.gz. pas_debug.log.1 is read when present; pas_debug.log is read only "
                 "when it is not. Timestamp is the log line's clock reading. No zone is read "
                 "from the line. The value is stored as if it were UTC, and the offset from UTC "
                 "is not established. A line with a single digit month, day or hour is left as "
                 "text.",
        "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "chryslerTarSpeed": {
        "name": "Chrysler - Tar GZ Road Speed Limits",
        "description": "Speed limit values (no road name is reported) from a pas_debug log inside "
                       "a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the log line's clock "
                 "reading. No zone is read from the line. "
                 "The value is stored as if it were UTC, "
                 "and the offset from UTC is not "
                 "established. A line with a single digit "
                 "month, day or hour is left as text. "
                 "Lines containing \"Speed limit invalid\" "
                 "are left out.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "alert-triangle",
    },
    "chryslerTarApInfo": {
        "name": "Chrysler - Tar GZ Access Point List",
        "description": "Wi-Fi SSID and signal lines, each shown with the BSSID and time of "
                       "the most recent \"Extracted BSSID\" line before it, from a pas_debug "
                       "log inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the clock reading of the "
                 "most recent \"Extracted BSSID\" line "
                 "before the SSID line, not of the SSID "
                 "line itself. No zone is read from the "
                 "line. The value is stored as if it were "
                 "UTC, and the offset from UTC is not "
                 "established. A line with a single digit "
                 "month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "wifi",
    },
    "chryslerTarVSpeed": {
        "name": "Chrysler - Tar GZ Vehicle Speed",
        "description": "Vehicle speed (kmph) from a pas_debug log inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "navigation",
    },
    "chryslerTarTransm": {
        "name": "Chrysler - Tar GZ Transmission Status",
        "description": "Transmission status from a pas_debug log inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "settings",
    },
    "chryslerTarBrake": {
        "name": "Chrysler - Tar GZ Brake Status",
        "description": "eBrakePedalStatus values, shown as Brake Pedal Pressed for 1 and Brake "
                       "Pedal Released for 0 with no source recorded for that mapping, each "
                       "with the coordinates last logged before it, from a pas_debug log "
                       "inside a "
                       "Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last coordinates "
                 "the parser read before the event line, from "
                 "either a 'Received Lat' line or a 'lat: ... "
                 "lon: ... heading:' line. They are blank when "
                 "the event's timestamp, less its last three "
                 "characters, differs from that of the last "
                 "'Received Lat' line, and stay blank until the "
                 "next coordinate line. The pairing is by line "
                 "order and is not a link the log records. Other "
                 "eBrakePedalStatus values are not listed and a "
                 "repeated row is listed once. Timestamp is the "
                 "log line's clock reading. No zone is read "
                 "from the line. The value is stored as if it "
                 "were UTC, and the offset from UTC is not "
                 "established. A line with a single digit month, "
                 "day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "octagon",
    },
    "chryslerTarEngineTemp": {
        "name": "Chrysler - Tar GZ Engine Temperature",
        "description": "The first two characters of the logged engine coolant temperature "
                       "value, each with the coordinates last logged before it, from a "
                       "pas_debug log "
                       "inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last "
                 "coordinates the parser read before the "
                 "event line, from either a 'Received Lat' "
                 "line or a 'lat: ... lon: ... heading:' "
                 "line. They are blank when the event's "
                 "timestamp, less its last three "
                 "characters, differs from that of the "
                 "last 'Received Lat' line, and stay blank "
                 "until the next coordinate line. The "
                 "pairing is by line order and is not a "
                 "link the log records. Only the first two "
                 "characters of the value after \"iTemp "
                 "C:\" are kept, so a three digit or signed "
                 "value is not shown in full. Timestamp "
                 "is the log line's clock reading. No zone "
                 "is read from the line. The value is "
                 "stored as if it were UTC, and the offset "
                 "from UTC is not established. A line "
                 "with a single digit month, day or hour "
                 "is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "chryslerTarInteriorTemp": {
        "name": "Chrysler - Tar GZ Interior Temperature",
        "description": "Vehicle interior temperature value as logged (unit not established), "
                       "each with the coordinates last logged before it, from a pas_debug log "
                       "inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last "
                 "coordinates the parser read before the "
                 "event line, from either a 'Received Lat' "
                 "line or a 'lat: ... lon: ... heading:' "
                 "line. They are blank when the event's "
                 "timestamp, less its last three "
                 "characters, differs from that of the "
                 "last 'Received Lat' line, and stay blank "
                 "until the next coordinate line. The "
                 "pairing is by line order and is not a "
                 "link the log records. The value is the "
                 "text after \"after scaling:\"; the column "
                 "header gives degrees Celsius and no unit "
                 "is read from the line. Timestamp is the "
                 "log line's clock reading. No zone is "
                 "read from the line. The value is stored "
                 "as if it were UTC, and the offset from "
                 "UTC is not established. A line with a "
                 "single digit month, day or hour is left "
                 "as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "chryslerTarTirePressure": {
        "name": "Chrysler - Tar GZ Tire Pressure",
        "description": "Tire pressure readings for the position tokens the parser recognises "
                       "(REAR_LEFT, REAR_REAR, FRONT_LEFT, FRONT_REAR as logged), each with "
                       "the coordinates last logged before it, from a pas_debug log "
                       "inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last coordinates "
                 "the parser read before the event line, from "
                 "either a 'Received Lat' line or a 'lat: ... "
                 "lon: ... heading:' line. They are blank when "
                 "the event's timestamp, less its last three "
                 "characters, differs from that of the last "
                 "'Received Lat' line, and stay blank until the "
                 "next coordinate line. The pairing is by line "
                 "order and is not a link the log records. "
                 "REAR_REAR is shown as Rear Right Tire and "
                 "FRONT_REAR as Front Right Tire. A line with "
                 "any other position token produces no row. "
                 "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "disc",
    },
    "chryslerTarGearState": {
        "name": "Chrysler - Tar GZ Gear State",
        "description": "eGearState values (shown as Park for 1, Neutral for 2, Drive for 3 and "
                       "Reverse for 4; no source for that mapping is recorded and other values "
                       "are not listed), each with the coordinates last logged before it, from a "
                       "pas_debug log inside "
                       "a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last coordinates "
                 "the parser read before the event line, from "
                 "either a 'Received Lat' line or a 'lat: ... "
                 "lon: ... heading:' line. They are blank when "
                 "the event's timestamp, less its last three "
                 "characters, differs from that of the last "
                 "'Received Lat' line, and stay blank until the "
                 "next coordinate line. The pairing is by line "
                 "order and is not a link the log records. "
                 "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "sliders",
    },
    "chryslerTarOutTemp": {
        "name": "Chrysler - Tar GZ Outside Temperature",
        "description": "Outside air temperature from a pas_debug log inside a Chrysler "
                       "[H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "chryslerTarDoor": {
        "name": "Chrysler - Tar GZ Door Status",
        "description": "Driver door and trunk lift gate ajar status (0 shown as Closed, 1 "
                       "as Open; no source for that mapping is recorded, and other doors "
                       "are not reported), each with the coordinates last logged before it, "
                       "from a pas_debug log "
                       "inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are the last coordinates "
                 "the parser read before the event line, from "
                 "either a 'Received Lat' line or a 'lat: ... "
                 "lon: ... heading:' line. They are blank when "
                 "the event's timestamp, less its last three "
                 "characters, differs from that of the last "
                 "'Received Lat' line, and stay blank until the "
                 "next coordinate line. The pairing is by line "
                 "order and is not a link the log records. A row "
                 "is produced only for _AJAR_ lines naming "
                 "TRUNK_LIFT_GATE or containing DRIVE. Timestamp "
                 "is the log line's clock reading. No zone is "
                 "read from the line. The value is stored as if "
                 "it were UTC, and the offset from UTC is not "
                 "established. A line with a single digit month, "
                 "day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "log-out",
    },
    "chryslerTarOdometer": {
        "name": "Chrysler - Tar GZ Odometer",
        "description": "Odometer values (each shown with the time of the most recent "
                       "CAppLinkService line before it, not the time of the odometer line itself) "
                       "from a pas_debug log inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the clock reading of the most "
                 "recent CAppLinkService line before the "
                 "odometer line, not of the odometer line "
                 "itself, and is blank when there is none. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "activity",
    },
    "chryslerTarCurRoad": {
        "name": "Chrysler - Tar GZ Current Road",
        "description": "Current road from a pas_debug log inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Timestamp is the log line's clock reading. No "
                 "zone is read from the line. The value is "
                 "stored as if it were UTC, and the offset from "
                 "UTC is not established. A line with a single "
                 "digit month, day or hour is left as text.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "map",
    },
    "chryslerTarVehicle": {
        "name": "Chrysler - Tar GZ Vehicle Info",
        "description": "Vehicle identity (make/model/year/VIN/platform) from a pas_debug log "
                       "inside a Chrysler [H-M]_*.tar.gz.",
        "author": "@JaysonU25", "version": "0.2", "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29", "requirements": "none", "category": "Chrysler Vehicles",
        "notes": "Make, model, model year, VIN and "
                 "platform version values, also written "
                 "to the device information log. Make, "
                 "model and year show the last value "
                 "seen; Platform Version is the Version "
                 "Number from a USBUPDT_MID line.", "paths": ('*/[H-M]_*.tar.gz',),
        "output_types": "standard", "artifact_icon": "truck",
    },
}

import os
import tarfile
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logdevinfo

_GEAR = {'1': 'Gear is in Park', '2': 'Gear is in Neutral', '3': 'Gear is in Drive',
         '4': 'Gear is in Reverse'}
_TIRE = {'REAR_LEFT': 'Rear Left Tire', 'REAR_REAR': 'Rear Right Tire',
         'FRONT_LEFT': 'Front Left Tire', 'FRONT_REAR': 'Front Right Tire'}


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


def _read_log(file_found):
    with tarfile.open(file_found, 'r') as tar:
        member = None
        for name in ('pas_debug.log.1', 'pas_debug.log'):
            try:
                member = tar.extractfile(name)
            except KeyError:
                member = None
            if member:
                break
        return member.read().decode('cp437', errors='backslashreplace') if member else ''


def _parse(context):
    sect = {k: [] for k in ('dev', 'speed', 'apinfo', 'vspeed', 'transm', 'outtemp', 'odometer',
                            'curroad', 'brake', 'engine', 'interior', 'tp', 'gear', 'door')}
    make, model, yearc, vins, platforms = '', '', '', [], []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if not file_found.endswith('.tar.gz') or os.stat(file_found).st_size == 0:
            continue
        source_path = file_found
        basename = os.path.basename(file_found)
        try:
            content = _read_log(file_found)
        except (KeyError, tarfile.TarError):
            continue
        bssid, ts_apinfo, ts_link = '', '', ''
        timestamp_loc, latitude, longitude = '', '', ''
        for line in content.splitlines():
            try:
                if ': lat: ' in line and 'lon:' in line and 'heading: ' in line:
                    segs = line.split(': lat: ')
                    if len(segs) > 1:
                        parts = segs[1].split(',')
                        latitude = parts[0].strip()
                        longitude = parts[1].split('lon:')[1].strip()
                        heading = parts[2].split('heading: ')[1].strip()
                        sect['dev'].append((_ts(timeorder(line)), latitude, longitude, heading,
                                            basename))
                if '= Speed Limit:' in line and 'Speed limit invalid' not in line:
                    sect['speed'].append((_ts(timeorder(line)), '', line.split('=')[1].strip(),
                                          basename))
                if 'WIFI_MID' in line:
                    if 'Extracted BSSID' in line:
                        bssid = line.split('=')[-1].strip()
                        ts_apinfo = _ts(timeorder(line))
                    if 'SSID:' in line:
                        ssid = line.split(';')[0].split(':')[-1].strip()
                        signal = line.split(';')[-1].split(',')[-1].split(':')[-1].strip()
                        sect['apinfo'].append((ts_apinfo, bssid, ssid, signal, basename))
                if '] currentRoad' in line and 'nv_navigation' in line:
                    road = line.split('] [')[-1].split('] currentRoad')[0]
                    sect['curroad'].append((_ts(timeorder(line)), road, basename))
                if '[SAL_SWITCH_DISPLAY] Received speed:' in line:
                    speeds = line.split('[SAL_SWITCH_DISPLAY] Received speed:')[1].strip()
                    sect['vspeed'].append((_ts(timeorder(line)), speeds.split(' kmph')[0]))
                if 'Received Lat' in line:
                    timestamp_loc = timeorder(line)
                    loc = line.split('Received Lat ')[1].split(' ')
                    latitude, longitude = loc[0].strip(), loc[2].strip()
                if 'eBrakePedalStatus: ' in line and len(line.split('eBrakePedalStatus: ')) > 1:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    val = line.split('eBrakePedalStatus: ')[1].strip()
                    brake = 'Brake Pedal Pressed' if val == '1' else (
                        'Brake Pedal Released' if val == '0' else '')
                    row = (_ts(ts_str), brake, latitude, longitude)
                    if brake and row not in sect['brake']:
                        sect['brake'].append(row)
                if 'GENERAL_ENGINE_COOLANT_TEMPERATURE_EVENTHandler' in line \
                        and len(line.split('=iTemp C: ')) > 1:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    etemp = line.split('=iTemp C: ')[1].strip()[0:2]
                    row = (_ts(ts_str), etemp, latitude, longitude)
                    if etemp and row not in sect['engine']:
                        sect['engine'].append(row)
                if 'GENERAL_VEHICLE_INTERIOR_TEMPERATURE_EVENTHandler' in line \
                        and len(line.split('after scaling: ')) > 1:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    itemp = line.split('after scaling: ')[1].strip()
                    row = (_ts(ts_str), itemp, latitude, longitude)
                    if itemp and row not in sect['interior']:
                        sect['interior'].append(row)
                if 'TPM_A2_Callback' in line and len(line.split('=Published TIRE_PRESSURE')) > 1:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    tire, pressure = '', ''
                    for key, label in _TIRE.items():
                        if key in line:
                            tire, pressure = label, line.strip().split(' ')[-1]
                            break
                    row = (_ts(ts_str), tire, pressure, latitude, longitude)
                    if pressure and row not in sect['tp']:
                        sect['tp'].append(row)
                if 'eGearState = ' in line and len(line.split('eGearState = ')) > 1:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    gear = _GEAR.get(line.split('eGearState = ')[1].strip(), '')
                    row = (_ts(ts_str), gear, latitude, longitude)
                    if gear and row not in sect['gear']:
                        sect['gear'].append(row)
                if '_AJAR_' in line and 'error' not in line and 'Error' not in line:
                    ts_str = timeorder(line)
                    if ts_str[0:-3] != timestamp_loc[0:-3]:
                        latitude = longitude = ''
                    door = ''
                    if 'TRUNK_LIFT_GATE' in line:
                        val = line.split(' ')[-1].strip()
                        door = 'Trunk Lift Gate Closed' if val == '0' else (
                            'Trunk Lift Gate Open' if val == '1' else '')
                    elif 'DRIVE' in line:
                        val = line.split(' ')[-1].strip()[1]
                        door = 'Driver Door Closed' if val == '0' else (
                            'Driver Door Open' if val == '1' else '')
                    row = (_ts(ts_str), door, latitude, longitude)
                    if door and row not in sect['door']:
                        sect['door'].append(row)
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
                if '"vin":' in line:
                    vin = line.split('vin')[1].split(',')[0].split('"')[2]
                    if vin and vin not in vins:
                        vins.append(vin)
                if 'VIN got from GGC' in line:
                    vin = line.strip().split('=')[-1].strip()
                    if vin and vin not in vins:
                        vins.append(vin)
                if '"make"' in line:
                    make = line.strip().split(':')[-1].strip().replace('"', '')
                if 'Model_Id::' in line:
                    tail = line.split('Model_Id::')[1].split(' ')
                    model = f'{tail[0]} {tail[1]}'
                if '=Vehicle Model Year = ' in line:
                    yearc = line.split('=Vehicle Model Year = ')[1].strip()
            except (IndexError, ValueError, TypeError):
                continue

    vehicle = []
    if make:
        vehicle.append(('Make', make))
    if model:
        vehicle.append(('Model', model))
    if yearc:
        vehicle.append(('Model Year', yearc))
    for vin in vins:
        vehicle.append(('VIN', vin))
    for pver in platforms:
        vehicle.append(('Platform Version', pver))
    sect['vehicle'] = vehicle
    return sect, source_path


@artifact_processor
def chryslerTarGps(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Heading', 'Log Filename')
    return headers, sect['dev'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Road', 'Speed Limit', 'Log Filename')
    return headers, sect['speed'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarApInfo(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'BSSID', 'SSID', 'Signal Strength', 'Log Filename')
    return headers, sect['apinfo'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarVSpeed(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Vehicle Speed KMPH')
    return headers, sect['vspeed'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarTransm(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Transmission Status', 'Log Filename')
    return headers, sect['transm'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarBrake(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Brake Status', 'Latitude', 'Longitude')
    return headers, sect['brake'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarEngineTemp(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Engine Temp Degrees Celcius', 'Latitude', 'Longitude')
    return headers, sect['engine'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarInteriorTemp(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Interior Temp Degrees Celcius', 'Latitude', 'Longitude')
    return headers, sect['interior'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarTirePressure(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Tire', 'Tire Pressure', 'Latitude', 'Longitude')
    return headers, sect['tp'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarGearState(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Gear State', 'Latitude', 'Longitude')
    return headers, sect['gear'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarOutTemp(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Temperature', 'Log Filename')
    return headers, sect['outtemp'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarDoor(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Door Status', 'Latitude', 'Longitude')
    return headers, sect['door'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarOdometer(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Odometer', 'Log Filename')
    return headers, sect['odometer'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarCurRoad(context):
    sect, source_path = _parse(context)
    headers = (('Timestamp', 'datetime'), 'Current Road', 'Log Filename')
    return headers, sect['curroad'], context.get_relative_path(source_path)


@artifact_processor
def chryslerTarVehicle(context):
    sect, source_path = _parse(context)
    for field, value in sect['vehicle']:
        logdevinfo(f"{field} from pas_debug tar.gz: {value}")
    return ('Field', 'Value'), sect['vehicle'], context.get_relative_path(source_path)
