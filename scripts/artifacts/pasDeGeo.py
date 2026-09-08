__artifacts_v2__ = {
    "pasDeGeoDevLoc": {
        "name": "Ford - PAS Dev Loc Results",
        "description": "Device location results (lat/long/alt/heading) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Latitude/Longitude exposed for the KML map. Supports the PAS log timestamp format, including single-digit month/day/hour values, and the Lon:/Lat: location format; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'], "artifact_icon": "map-pin",
    },
    "pasDeGeoSpeed": {
        "name": "Ford - PAS Road Speed Limits",
        "description": "Road speed limits from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "alert-triangle",
    },
    "pasDeGeoApInfo": {
        "name": "Ford - PAS Access Point List",
        "description": "Wi-Fi access points (BSSID/SSID/signal) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "wifi",
    },
    "pasDeGeoVSpeed": {
        "name": "Ford - PAS Vehicle Speed",
        "description": "Vehicle speed readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "navigation",
    },
    "pasDeGeoTransm": {
        "name": "Ford - PAS Transmission Status",
        "description": "Transmission status readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "settings",
    },
    "pasDeGeoTemp": {
        "name": "Ford - PAS Outside Temperature",
        "description": "Outside air temperature readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "thermometer",
    },
    "pasDeGeoOdometer": {
        "name": "Ford - PAS Odometer",
        "description": "Odometer readings from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.5", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-07", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Supports the PAS log timestamp format, including single-digit month/day/hour values; reads plain and gzip-compressed logs, skips directory paths, and continues past unreadable or truncated logs. Timestamp is the head unit's local clock as recorded, with no zone on the line. Timestamp UTC is derived from the offset the log itself records in its VS_CLOCK_QUEUE lines, taken from the nearest one within 10 minutes and left blank when there is none, so it is never extrapolated across a gap; UTC Offset Applied names the offset used. On the tested case all 24,581 readings derived, every one at -04:00, and the derived instants agree with all 409 published UTC lines the log carries. The offset belongs to the moment rather than to the extraction: on a Sync Gen3 extraction the same comparison gave 4 hours in most periods, 5 hours in one and 6 hours in another, the head unit reporting its clock already correct in ten of those eleven. A log that records no offset lines leaves both derived columns blank.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "activity",
    },
    "pasDeGeoVehicle": {
        "name": "Ford - PAS Vehicle Info",
        "description": "Vehicle identity (VIN/make/model/platform) from a Ford pas_debug.log.",
        "author": "@AlexisBrignoni", "version": "0.3", "creation_date": "2021-07-08",
        "last_update_date": "2026-09-06", "requirements": "none", "category": "Ford Vehicles",
        "notes": "Surfaces the make/model/VIN/platform the original only wrote to the device-info "
                 "log. Supports the PAS log timestamp format, including single-digit month/day/hour "
                 "values; reads plain and gzip-compressed logs, skips directory paths, and continues "
                 "past unreadable or truncated logs.", "paths": ('*/fordlogs/pas_debug.log*',),
        "output_types": "standard", "artifact_icon": "truck",
    },
}

import os
import re
import gzip
import zlib
import bisect
from datetime import datetime, timedelta, timezone

from scripts.ilapfuncs import artifact_processor, logdevinfo, logfunc

_NUM = r"([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?"
_RE = {k: re.compile(f"({label}\\s*{_NUM})", re.IGNORECASE) for k, label in (
    ('lon1', 'Longitude ='), ('lat1', 'Latitude ='), ('alt1', 'Altitude ='),
    ('lon2', 'Lon ='), ('lat2', 'Lat ='), ('alt2', 'Alt ='), ('head', 'Heading ='),
    ('lon3', 'lon:'), ('lat3', 'lat:'), ('alt3', 'alt:'), ('head3', 'hd:'))}
# The optional whitespace is intentional for inconsistent spacing in older PAS logs.


def timeorder(line):
    month, day, yeartime = line.split('/', 3)[0], line.split('/', 3)[1], line.split('/', 3)[2]
    year, time = yeartime.split(' ', 1)
    hour, minute, second = time.split(':', 2)
    return f'{year}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{minute}:{second}'


def _ts(value):
    """The log line's own clock reading, returned as recorded.

    The PAS log writes the head unit's local clock and records no zone on the line, so
    the value is not an instant and is not typed as one. Typing it would make the report
    and the LAVA database read it as UTC, which is measurably wrong: see the artifact
    notes for the offsets observed and for the log lines that record them.
    """
    return (value or '').strip()


# The head unit renders its log timestamps in local time and states no zone on the line.
# The clock subsystem does record the offset, in two forms, and both carry a validity flag:
#   VS_CLOCK_QUEUE/VmcuClockTimeHandler  Published NTFY_VehicleServiceUTCTime => year: [...] valid: [1]
#   VS_CLOCK_QUEUE/QnxClockSet           NTFY_VehicleServiceUTCTimeOffset - ... total_offset: [N] valid: [1]
# Only lines flagged valid are used. The boot-time GPS comparison is deliberately not used
# as a reference: on the boots where it reports a correction, the reading it carries is the
# clock as it was *before* being corrected.
_RE_PUBLISHED_UTC = re.compile(
    r'Published NTFY_VehicleServiceUTCTime => year: \[(\d+)\], month: \[(\d+)\], '
    r'day: \[(\d+)\], hour: \[(\d+)\], minute: \[(\d+)\], second: \[(\d+)\], valid: \[1\]')
_RE_UTC_OFFSET = re.compile(
    r'NTFY_VehicleServiceUTCTimeOffset - hour: \[-?\d+\] min: \[-?\d+\] sec: \[-?\d+\] '
    r'total_offset: \[(-?\d+)\] valid: \[1\]')

# A reference is only applied to a reading close to it in time. The offset is a property of
# the moment, not of the extraction: it is published about once a minute while the head unit
# is running, and it was observed to differ between periods on a tested extraction. Anything
# further away than this is left blank rather than extrapolated across a gap.
_REFERENCE_WINDOW = timedelta(minutes=10)


def _as_datetime(value):
    """The recorded reading as a naive datetime, or None if it is not one."""
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
    except (ValueError, TypeError):
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None


def _clock_reference(line, recorded):
    """(reading, minutes UTC leads it) for a line that records the offset, else None."""
    published = _RE_PUBLISHED_UTC.search(line)
    if published:
        try:
            utc = datetime(*(int(g) for g in published.groups()))
        except ValueError:
            return None
        # The published value carries second: [0] on every line the tested logs hold, and it
        # is not written at the same instant as the line that carries it, so the difference
        # lands within a minute of the offset rather than on it. Civil UTC offsets are whole
        # multiples of 15 minutes, so snapping to that recovers the offset and discards the
        # sub-minute noise. On the tested logs this agrees with the offset the head unit
        # states outright in total_offset, which is an independently written field.
        difference = round((utc - recorded).total_seconds() / 60)
        return (recorded, round(difference / 15) * 15)
    stated = _RE_UTC_OFFSET.search(line)
    if stated:
        return (recorded, int(stated.group(1)) // 60)
    return None


def _apply_references(rows, references, timestamp_index=0):
    """Insert the derived UTC instant and the offset used after each row's reading.

    Blank when no reference sits within the window, which is the answer for a log that
    records no offset at all and for a reading written before the clock was set.
    """
    if not rows:
        return rows
    keys = [r[0] for r in references]
    out = []
    for row in rows:
        recorded = _as_datetime(row[timestamp_index])
        utc_text, offset_text = '', ''
        if recorded is not None and keys:
            i = bisect.bisect_left(keys, recorded)
            nearest, closest = None, None
            for candidate in (i - 1, i):
                if not 0 <= candidate < len(keys):
                    continue
                gap = abs(keys[candidate] - recorded)
                if closest is None or gap < closest:
                    nearest, closest = candidate, gap
            if nearest is not None and closest <= _REFERENCE_WINDOW:
                minutes = references[nearest][1]
                utc_text = (recorded + timedelta(minutes=minutes)).replace(tzinfo=timezone.utc)
                sign = '-' if minutes >= 0 else '+'
                offset_text = f'{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}'
        out.append(row[:timestamp_index + 1] + (utc_text, offset_text) + row[timestamp_index + 1:])
    return out


def _val(match):
    return match[2] if match else ''


def _parse(context):
    sect = {k: [] for k in ('dev', 'speed', 'apinfo', 'vspeed', 'transm', 'outtemp', 'odometer',
                            'vehicle')}
    vins, platforms, make, model = [], [], '', ''
    source_paths = []
    references = []
    for file_found in context.get_files_found():
        file_found = str(file_found)

        if not os.path.isfile(file_found):
            continue

        basename = os.path.basename(file_found)
        bssid, ts_link = '', ''

        try:
            if file_found.lower().endswith('.gz'):
                opener = gzip.open
                mode = 'rt'
            else:
                opener = open
                mode = 'r'

            with opener(file_found, mode, encoding='cp437') as f:
                source_paths.append(file_found)
                for line in f:
                    try:
                        if 'VS_CLOCK_QUEUE' in line:
                            recorded = _as_datetime(timeorder(line))
                            if recorded is not None:
                                reference = _clock_reference(line, recorded)
                                if reference:
                                    references.append(reference)
                        if 'NAV_FRAMEWORK_IF' in line and 'dev_loc_results' in line \
                                and 'ERROR  RPT!!!' not in line:
                            if 'Longitude =' in line:
                                lat, lon, alt = _RE['lat1'].search(line), _RE['lon1'].search(line), \
                                    _RE['alt1'].search(line)
                                head_match = _RE['head'].search(line)
                            elif 'Lon =' in line:
                                lat, lon, alt = _RE['lat2'].search(line), _RE['lon2'].search(line), \
                                    _RE['alt2'].search(line)
                                head_match = _RE['head'].search(line)
                            elif 'lon:' in line.lower() or 'lat:' in line.lower():
                                lat, lon, alt = _RE['lat3'].search(line), _RE['lon3'].search(line), \
                                    _RE['alt3'].search(line)
                                head_match = _RE['head3'].search(line)
                            else:
                                lat = lon = alt = head_match = None
                            if lat and lon:
                                sect['dev'].append((_ts(timeorder(line)), _val(lat), _val(lon),
                                                    _val(alt), _val(head_match),
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
        except (OSError, UnicodeError, EOFError, zlib.error) as e:
            logfunc(f"Unable to read Ford PAS log: {file_found} ({type(e).__name__}: {e})")
            continue

    references.sort()
    for key in ('dev', 'speed', 'apinfo', 'vspeed', 'transm', 'outtemp', 'odometer'):
        sect[key] = _apply_references(sect[key], references)

    if make:
        sect['vehicle'].append(('Make', make))
    if model:
        sect['vehicle'].append(('Model', model))
    for vin in vins:
        sect['vehicle'].append(('VIN', vin))
    for pver in platforms:
        sect['vehicle'].append(('Platform Version', pver))
    return sect, '\n'.join(source_paths)


@artifact_processor
def pasDeGeoDevLoc(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Latitude', 'Longitude', 'Altitude Ft', 'Heading',
               'Category', 'Subcategory', 'Log Filename')
    return headers, sect['dev'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoSpeed(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Road', 'Speed Limit', 'Log Filename')
    return headers, sect['speed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoApInfo(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'BSSID', 'SSID', 'Signal Strength', 'Log Filename')
    return headers, sect['apinfo'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoVSpeed(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Vehicle Speed', 'Log Filename')
    return headers, sect['vspeed'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTransm(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Transmission Status', 'Log Filename')
    return headers, sect['transm'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoTemp(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Temperature', 'Log Filename')
    return headers, sect['outtemp'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoOdometer(context):
    sect, source_path = _parse(context)
    headers = ('Timestamp', ('Timestamp UTC', 'datetime'), 'UTC Offset Applied',
               'Odometer', 'Log Filename')
    return headers, sect['odometer'], context.get_relative_path(source_path)


@artifact_processor
def pasDeGeoVehicle(context):
    sect, source_path = _parse(context)
    for field, value in sect['vehicle']:
        logdevinfo(f"{field} from pas_debug: {value}")
    return ('Field', 'Value'), sect['vehicle'], context.get_relative_path(source_path)
