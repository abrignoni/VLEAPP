__artifacts_v2__ = {
    "Favorite_Places": {
        "name": "Favorite places",
        "description": "Saved/recent navigation places (label, address, coordinates) from Ford "
                       "places storage.",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Latitude/Longitude are exposed for the KML map.",
        "paths": ('*/recents_storage', '*/favorites_storage'),
        "output_types": ['html', 'tsv', 'timeline', 'lava', 'kml'],
        "artifact_icon": "map-pin",
        "function": "get_fav_places",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def get_fav_places(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, 'r', encoding='cp437') as f:
            place_id = label = address = latitude = longitude = ''
            for line in f:
                if "places {" in line and place_id != "":
                    label = label or "None"
                    address = address or "None"
                    row = (place_id, label, address, latitude, longitude)
                    if place_id and latitude and longitude and row not in data_list:
                        data_list.append(row)
                    place_id = label = address = latitude = longitude = ''
                if "id: " in line:
                    place_id = line.split('id: "')[1].strip()[:-1]
                if "label:" in line:
                    label = line.split('label: "')[1].strip()[:-1]
                if "lat: " in line:
                    latitude = line.split("lat: ")[1].strip()
                if "lon: " in line:
                    longitude = line.split("lon: ")[1].strip()
                if 'formatted_address: "' in line:
                    address = line.split('formatted_address: "')[1].strip()[:-1]
            label = label or "None"
            address = address or "None"
            row = (place_id, label, address, latitude, longitude)
            if place_id and latitude and longitude and row not in data_list:
                data_list.append(row)

    data_headers = ('ID', 'Label', 'Address', 'Latitude', 'Longitude')
    return data_headers, data_list, context.get_relative_path(source_path)
