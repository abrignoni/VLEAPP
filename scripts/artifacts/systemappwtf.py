__artifacts_v2__ = {
    "systemappwtfGps": {
        "name": "Kia - System App GPS Detail",
        "description": "GPS fixes (GpsLocationProvider reportLocation) scraped from Kia "
                       "system_app_wtf / tombstone logs.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2023-03-27",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Kia Vehicles",
        "notes": "Timestamp is the GpsLocationProvider millisecond epoch normalized to UTC; Date is "
                 "the raw log line time. Latitude/Longitude exposed for the KML map.",
        "paths": ('*/system_app_wtf@*.txt.gz', '*/tombstones/tombstone_*',
                  '*/system_app_crash@*.txt.gz', '*/SYSTEM_TOMBSTONE@*.txt.gz'),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'],
        "artifact_icon": "map-pin",
    },
    "systemappwtfBtCalls": {
        "name": "Kia - System App BT Calls",
        "description": "Bluetooth call tracker events scraped from Kia system_app_wtf / tombstone "
                       "logs.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2023-03-27",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Kia Vehicles",
        "notes": "Date is the raw log line time.",
        "paths": ('*/system_app_wtf@*.txt.gz', '*/tombstones/tombstone_*',
                  '*/system_app_crash@*.txt.gz', '*/SYSTEM_TOMBSTONE@*.txt.gz'),
        "output_types": "standard",
        "artifact_icon": "phone-call",
    },
}

import gzip

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc


def _read_lines(file_found):
    if file_found.endswith('.gz'):
        with gzip.open(file_found, 'rb') as f:
            return [line.decode(errors='backslashreplace') for line in f]
    with open(file_found, 'r', encoding='utf-8', errors='backslashreplace') as f:
        return f.readlines()


def _parse(context):
    gps, calls = [], []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        rel = context.get_relative_path(file_found)
        for x in _read_lines(file_found):
            fecha = ' '.join(x.split(' ', 2)[:2])
            if 'V/GpsLocationProvider' in x and 'reportLocation' in x:
                try:
                    rest = x.split('reportLocation')[1]
                    latlong = rest.split('timestamp: ')[0]
                    gpslong = latlong.split('long: ')[1]
                    gpslat = latlong.split('long: ')[0].split('lat: ')[1]
                    ms = x.split('timestamp: ')[1].strip()
                    gps.append((convert_unix_ts_to_utc(int(ms)), fecha, gpslat.strip(),
                                gpslong.strip(), rel, x.strip()))
                except (IndexError, ValueError):
                    pass
            if '[BTCallTracker]' in x and 'number=' in x:
                try:
                    if 'GET_CURRENT_CALLS  ' in x:
                        current = x.split('GET_CURRENT_CALLS  ')[1]
                        number = current.split(',', 11)[8].split('=')[1]
                        status = current.split(',', 11)[1]
                        calls.append((fecha, number, ' ', status, rel, x.strip()))
                    if '[BTCallTracker] poll: conn' in x and ']=null,' in x:
                        number = x.split(',number=')[1].split(',')[0]
                        state = x.split(',toa=')[0].split(',')[-1]
                        calls.append((fecha, number, ' ', state, rel, x.strip()))
                    elif '[BTCallTracker] poll: conn' in x:
                        datacall = x.split('addr: ')[1]
                        number = datacall.split(' ', 1)[0]
                        incoming = datacall.split(' ', 5)[2]
                        state = datacall.split(' ', 5)[4]
                        calls.append((fecha, number, incoming, state, rel, x.strip()))
                except (IndexError, ValueError):
                    pass
    return gps, calls, source_path


@artifact_processor
def systemappwtfGps(context):
    gps, _, source_path = _parse(context)
    data_headers = (('Timestamp', 'datetime'), 'Date', 'Latitude', 'Longitude', 'Source',
                    'Source Line')
    return data_headers, gps, context.get_relative_path(source_path)


@artifact_processor
def systemappwtfBtCalls(context):
    _, calls, source_path = _parse(context)
    data_headers = ('Date', 'Phone Number', 'Incoming', 'State', 'Source', 'Source Line')
    return data_headers, calls, context.get_relative_path(source_path)
