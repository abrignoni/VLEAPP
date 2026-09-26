__artifacts_v2__ = {
    "VW_MIB2_Trips": {
        "name": "Trip Data",
        "description": "Retrieve Trip Data from Volkswagen Vehicles",
        "author": "@posiwer",
        "version": "1.0",
        "date": "2026-01-05",
        "requirements": "none",
        "category": "Volkswagen Vehicle",
        "notes": "",
        "paths": ('*/*user1.db*'),
        "function": "get_Trips"
    }
}

import os
import sqlite3
import json
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import tsv

def get_Trips(files_found, report_folder, seeker, wrap_text, time_offset):
    file_found = str(files_found[0])

    if not file_found.endswith('user1.db'):
        return

    db = sqlite3.connect(file_found)
    cursor = db.cursor()

    cursor.execute('''SELECT id, latitude, longitude, 
                      DATETIME(unixtime, 'unixepoch') AS datetime, seqNo, tripId, gxHash, gyHash, forceSave 
                      FROM trips''')
    all_rows = cursor.fetchall()

    if len(all_rows) == 0:
        return

    headers = ['ID', 'Latitude', 'Longitude', 'Date & Time', 'Sequence Number', 'Trip ID', 'GX Hash', 'GY Hash', 'Force Save']

    report = ArtifactHtmlReport('Trips')
    report.start_artifact_report(report_folder, 'Trips')
    report.add_script()

    data_list = []
    unique_dates = set()

    for row in all_rows:
        data_list.append(row)
        unique_dates.add(row[3].split(' ')[0])

    sorted_dates = sorted(unique_dates, reverse=True)

    report.add_section_heading('Trips Table')
    report.write_artifact_data_table(headers, data_list, file_found)

    map_html = f"""
    <div>
        <label for="dateFilter" style="font-size: 16px; margin-right: 10px;">Select Date:</label>
        <select id="dateFilter" style="padding: 5px 10px; font-size: 16px;">
            <option value="all" selected >All Dates</option>
            {"".join(f'<option value="{date}">{date}</option>' for date in sorted_dates)}
        </select>
    </div>

    <div id="map" style="width: 100%; height: 500px; margin-bottom: 20px;"></div>

    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script>
        var map = L.map('map').setView([0, 0], 2);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);

        var tripsData = {json.dumps([{ 
            "latitude": row[1], 
            "longitude": row[2], 
            "datetime": row[3], 
            "seqNo": row[4], 
            "tripId": row[5] 
        } for row in all_rows])};

        function groupByTripId(data) {{
            return data.reduce((acc, item) => {{
                acc[item.tripId] = acc[item.tripId] || [];
                acc[item.tripId].push(item);
                return acc;
            }}, {{}});
        }}

        var groupedTrips = groupByTripId(tripsData);

        var startIcon = L.divIcon({{
            className: "custom-icon",
            html: '<div style="background-color: green; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        }});

        var endIcon = L.divIcon({{
            className: "custom-icon",
            html: '<div style="background-color: red; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        }});

        function clearMap() {{
            map.eachLayer(function(layer) {{
                if (layer instanceof L.Marker || layer instanceof L.Polyline) {{
                    map.removeLayer(layer);
                }}
            }});
        }}

        function drawTrips(selectedDate) {{
            clearMap();
            let allLatLngs = [];

            for (let tripId in groupedTrips) {{
                var trip = groupedTrips[tripId];

                if (selectedDate && !trip.some(p => p.datetime.startsWith(selectedDate))) {{
                    continue;
                }}

                trip.sort((a, b) => a.seqNo - b.seqNo);

                var startPoint = trip[0];
                var endPoint = trip[trip.length - 1];

                if (startPoint.latitude && startPoint.longitude) {{
                    L.marker([startPoint.latitude, startPoint.longitude], {{ icon: startIcon }})
                        .addTo(map)
                        .bindPopup(`<b>Start Point</b><br>Lat: ${{startPoint.latitude}}, Lon: ${{startPoint.longitude}}, Date: ${{startPoint.datetime}}`);
                }}

                if (endPoint.latitude && endPoint.longitude) {{
                    L.marker([endPoint.latitude, endPoint.longitude], {{ icon: endIcon }})
                        .addTo(map)
                        .bindPopup(`<b>End Point</b><br>Lat: ${{endPoint.latitude}}, Lon: ${{endPoint.longitude}}, Date: ${{endPoint.datetime}}`);
                }}

                var lineCoordinates = trip.map(point => [point.latitude, point.longitude]);
                var polyline = L.polyline(lineCoordinates, {{ color: 'blue' }}).addTo(map);

                allLatLngs = allLatLngs.concat(lineCoordinates);
            }}

            if (allLatLngs.length > 0) {{
                map.fitBounds(allLatLngs);
            }}
        }}

        document.getElementById('dateFilter').addEventListener('change', function() {{
            var selectedDate = this.value;
            if (selectedDate === 'all') {{
                selectedDate = null;
            }}
            drawTrips(selectedDate);
        }});

        drawTrips(null);
    </script>
    """

    report.add_section_heading('Trips Map')
    report.add_trips_map(map_html)

    tsv(report_folder, headers, data_list, 'Trips')

    json_path = os.path.join(report_folder, 'trips.json')
    with open(json_path, mode='w', encoding='utf-8') as json_file:
        json.dump([{headers[i]: row[i] for i in range(len(headers))} for row in data_list], json_file, indent=4, ensure_ascii=False)

    # Parking Status
    cursor.execute('''SELECT id, DATETIME(visitTime, 'unixepoch') AS visitTime, latitude, longitude, tripId, DATETIME(lastDecay, 'unixepoch') AS lastDecay, duration_mins, description 
                      FROM parkingStatus''')
    all_rows = cursor.fetchall()

    if len(all_rows) == 0:
        return

    headers = ['ID', 'Visit Time', 'Latitude', 'Longitude', 'Trip ID', 'Last Decay', 'Duration (mins)', 'Description']

    report = ArtifactHtmlReport('Parking Status')
    report.start_artifact_report(report_folder, 'Parking Status')
    report.add_script()

    data_list = []

    for row in all_rows:
        data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]))

    report.add_section_heading('Parking Status Table')
    report.write_artifact_data_table(headers, data_list, file_found)

    map_html = f"""
    <div id="map" style="width: 100%; height: 500px; margin-bottom: 20px;"></div>

    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script>
        var map = L.map('map').setView([0, 0], 2);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);

        var parkingData = {json.dumps([{ 
            "id": row[0], 
            "latitude": row[2], 
            "longitude": row[3], 
            "visitTime": row[1]
        } for row in all_rows])};

        parkingData.forEach(function (point) {{
            if (point.latitude && point.longitude) {{
                L.marker([point.latitude, point.longitude]).addTo(map)
                    .bindPopup(`<b>Parking Point</b><br>ID: ${'{point.id}'}<br>Visit Time: ${'{point.visitTime}'}<br>Lat: ${'{point.latitude}'}<br>Lon: ${'{point.longitude}'}`);
            }}
        }});
    </script>
    """

    report.add_section_heading('Parking Status Map')
    report.add_trips_map(map_html)

    tsv(report_folder, headers, data_list, 'Parking Status')

    db.close()
