__artifacts_v2__ = {
    "Location_logs": {
        "name": "Location Logs",
        "description": "GPS location fixes (with accuracy, speed, course) parsed from Chrysler "
                       "JSR179 persistent logs.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "Latitude/Longitude are exposed for the KML map.",
        "paths": ('*/persistentLogs/*/Log*',),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'],
        "artifact_icon": "map-pin",
        "function": "get_location_logs",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def get_location_logs(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                if "JSR179InterfaceImpl [INFO] " not in line:
                    continue
                splits = line.split(" ")
                date = splits[0].strip()
                time = splits[1].strip()[0:-4]
                method = "N/A" if splits[-2] == ";" else splits[-2][0:-1]
                azimuth = splits[-5][0:-1]
                speed = splits[-7][0:-1]
                course = splits[-9][0:-1]
                v_acc = splits[-14][0:-1]
                h_acc = splits[-17][0:-1]
                altitude = splits[-20][0:-1]
                zip_code = "Not found" if splits[-22] == ";" else splits[-22][0:-1]
                longitude = splits[-25][0:-1]
                latitude = splits[-27][0:-1]
                row = (date, time, latitude, longitude, zip_code, altitude, h_acc, v_acc, course,
                       speed, azimuth, method)
                if date and time and latitude and longitude and row not in data_list:
                    data_list.append(row)

    data_headers = ('Date', 'Time', 'Latitude', 'Longitude', 'Zip Code', 'Altitude',
                    'Horizontal Accuracy', 'Vertical Accuracy', 'Course', 'Speed', 'Azimuth',
                    'Location Method')
    return data_headers, data_list, context.get_relative_path(source_path)
