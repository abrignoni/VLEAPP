__artifacts_v2__ = {
    "logparser": {
        "name": "RAM - GPS Locations from Logs",
        "description": "GPS locations (KONA-LIB LocationDistributor) parsed from RAM 1500 "
                       "persistent logs.",
        "author": "@AlexisBrignoni",
        "version": "0.2",
        "creation_date": "2024-04-06",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "RAM Vehicles",
        "notes": "Timestamp is the log's epoch normalized to UTC. Latitude/Longitude exposed for "
                 "the KML map. (Shares the persistentLogs/*/Log* path with the Chrysler Location "
                 "Logs artifact; each only matches its own log lines.)",
        "paths": ('*/persistentLogs/*/Log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'],
        "artifact_icon": "map-pin",
    }
}

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc

_MARKER = '[INFO] LocationDistributor[KONA-LIB] Location details: '


@artifact_processor
def logparser(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        basename = file_found.rsplit('/', 1)[-1]
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                if _MARKER not in line:
                    continue
                try:
                    parts = line.split(_MARKER)[1].split(';')
                    latitude = parts[1].split(' ')[2]
                    longitude = parts[2].split(' ')[2]
                    altitude = parts[4].split(' ')[2]
                    horzac = parts[5].split(' ')[3]
                    vertac = parts[6].split(' ')[3]
                    times = convert_unix_ts_to_utc(int(parts[7].split(' ')[3]))
                    course = parts[8].split(' ')[2]
                    speed = parts[9].split(' ')[2]
                    azimuth = parts[10].split(' ')[2]
                except (IndexError, ValueError):
                    continue
                data_list.append((times, latitude, longitude, horzac, vertac, altitude, course,
                                  speed, azimuth, basename))

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Horizontal Accuracy',
                    'Vertical Accuracy', 'Altitude', 'Course', 'Speed', 'Azimuth', 'Log Filename')
    return data_headers, data_list, context.get_relative_path(source_path)
