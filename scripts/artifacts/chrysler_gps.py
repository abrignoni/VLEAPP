__artifacts_v2__ = {
    "chryslerGps": {
        "name": "Chrysler - GPS",
        "description": "GPS latitude/longitude fixes scraped from Chrysler slog files.",
        "author": "Joe Dinsmoor",
        "version": "0.2",
        "creation_date": "2023-06-05",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are exposed for the KML map. Each longitude is paired with "
                 "the most recently seen latitude, so fixes split across consecutive log lines are "
                 "captured (the original required both on one line and could raise on a "
                 "latitude-only line).",
        "paths": ('*/log/slogs*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'],
        "artifact_icon": "map-pin",
    }
}

import re

from scripts.ilapfuncs import artifact_processor

_LAT_RE = re.compile(r"Latitude\sread\sfrom\sPS:\s([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))"
                     r"(?:[Ee]([+-]?\d+))?")
_LON_RE = re.compile(r"Longitude\sread\sfrom\sPS:\s([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))"
                     r"(?:[Ee]([+-]?\d+))?")


def _num(match):
    # re.findall returns (value, exponent) tuples; rebuild the numeric string.
    value, exp = match
    return value + ('e' + exp if exp else '')


@artifact_processor
def chryslerGps(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        last_lat = None
        try:
            with open(file_found, 'r', encoding='ISO-8859-1') as f:
                for line in f:
                    line_clean = (bytes(str(line), 'utf-8')
                                  .decode('unicode_escape', errors='replace')
                                  .encode('ascii', 'ignore').decode('ascii', errors='replace'))
                    if 'Latitude' in line_clean:
                        lats = [_num(m) for m in _LAT_RE.findall(line_clean)]
                        if lats:
                            last_lat = lats[0]
                    if 'Longitude' in line_clean:
                        lons = [_num(m) for m in _LON_RE.findall(line_clean)]
                        if lons and last_lat is not None:
                            pair = (last_lat, lons[0])
                            if pair not in data_list:
                                data_list.append(pair)
                            last_lat = None
        except (PermissionError, UnicodeDecodeError):
            continue

    data_headers = ('Latitude', 'Longitude')
    return data_headers, data_list, context.get_relative_path(source_path)
