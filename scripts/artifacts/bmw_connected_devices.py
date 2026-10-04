__artifacts_v2__ = {
    "bmw_connected_apple_devices": {
        "name": "Connected Apple Devices",
        "description": "Media library records from the head unit's iap2 stores "
                       "(iap2_library table), with the identifier parsed from each store's "
                       "file name and the device UDID each record holds.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "BMW Vehicles",
        "notes": "On the tested image each store's file name carried an identifier tagged btmac "
                 "or serial. That the unit keeps one store per device is not established here. "
                 "The identifier is parsed from the file name and reported alongside the device "
                 "UDID held in the iap2_library table, so the two can be compared rather than one "
                 "being inferred from the other. Identifier Type and Identifier are parsed from "
                 "the store's file name and are blank when the name carries no identifier, so "
                 "they do not separate two such stores, and Source File names the store each row "
                 "came from. This artifact reads only the .db.backup copies, because the declared "
                 "path matches nothing else, so what is reported is the content of those copies, "
                 "which is not necessarily the state at acquisition. On the tested image no "
                 "other copy of these stores was found. A row is one iap2_library record; it does "
                 "not establish who was in the vehicle, and what a library row named for a "
                 "streaming service represents is not established.",
        "paths": ('*/iap2_*.db.backup',),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "2024 BMW MGU | 12 rows",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "bmw_connected_device_media": {
        "name": "Connected Device Media",
        "description": "Media items the head unit indexed from connected Apple devices, "
                       "with title, artist, album, genre and duration as the unit recorded "
                       "them.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "BMW Vehicles",
        "notes": "From iap2_media_item joined to the artist, album, album artist, genre and "
                 "composer tables in the same store. Playback duration is reported as "
                 "stored because nothing available here establishes its units. The type and "
                 "rating columns are undocumented integers and are also reported as stored. "
                 "The query reads no play count or last played column, so a row does not show "
                 "that an item was played. The identifier columns carry the value from the "
                 "store's file name so a row can be "
                 "attributed to the device it came from. They are blank when the store's file name"
                 " carries no identifier, so Identifier does not separate two such stores, and "
                 "Source File names the store each row came from.",
        "paths": ('*/iap2_*.db.backup',),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "2024 BMW MGU | 220 rows",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
}

import os
import re
import sqlite3

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly

# The store directory names the device: iap2_[btmac:..] or iap2_[serial:..].
# The seeker cannot stage a colon on every filesystem and rewrites it to an
# underscore, so accept either separator rather than the archive spelling only.
_DEVICE_KEY = re.compile(r'iap2_\[(btmac|serial)[:_]([^\]]+)\]')


def _device_from_path(path):
    """The identifier kind and value the unit named this store by."""
    match = _DEVICE_KEY.search(os.path.basename(path))
    if not match:
        return '', ''
    return match.group(1), match.group(2)


def _iap2_stores(context):
    """Every iAP2 store the seeker matched."""
    for file_found in sorted(str(f) for f in context.get_files_found()):
        if os.path.isdir(file_found) or not file_found.endswith('.db.backup'):
            continue
        yield file_found


@artifact_processor
def bmw_connected_apple_devices(context):
    data_list = []
    source_paths = []
    for store in _iap2_stores(context):
        db = open_sqlite_db_readonly(store)
        if db is None:
            continue
        cursor = db.cursor()
        try:
            cursor.execute('''
                SELECT library_id, name, device_udid, library_uid, revision, is_itunes
                FROM iap2_library
                ORDER BY library_id
            ''')
            rows = cursor.fetchall()
        except sqlite3.Error:
            db.close()
            continue
        db.close()
        source_paths.append(store)
        kind, value = _device_from_path(store)
        for row in rows:
            data_list.append((kind, value, row[1], row[2], row[3], row[4], row[5],
                              row[0], context.get_relative_path(store)))

    data_headers = ('Identifier Type', 'Identifier', 'Library Name', 'Device UDID',
                    'Library UID', 'Revision (as stored)', 'Is iTunes (as stored)',
                    'Library ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def bmw_connected_device_media(context):
    data_list = []
    source_paths = []
    for store in _iap2_stores(context):
        db = open_sqlite_db_readonly(store)
        if db is None:
            continue
        cursor = db.cursor()
        try:
            cursor.execute('''
                SELECT m.title, ar.artist, al.album, aa.albumartist, g.genre,
                       c.composer, m.playback_duration, m.type, m.rating,
                       m.album_track_number, m.is_compilation, l.name
                FROM iap2_media_item m
                LEFT JOIN iap2_artist ar ON ar.artist_id = m.artist_id
                LEFT JOIN iap2_album al ON al.album_id = m.album_id
                LEFT JOIN iap2_albumartist aa ON aa.albumartist_id = m.albumartist_id
                LEFT JOIN iap2_genre g ON g.genre_id = m.genre_id
                LEFT JOIN iap2_composer c ON c.composer_id = m.composer_id
                LEFT JOIN iap2_library l ON l.library_id = m.library_id
                ORDER BY ar.artist, al.album, m.album_track_number, m.rowid, ar.rowid, al.rowid, aa.rowid, g.rowid, c.rowid, l.rowid
            ''')
            rows = cursor.fetchall()
        except sqlite3.Error:
            db.close()
            continue
        db.close()
        if not rows:
            continue
        source_paths.append(store)
        kind, value = _device_from_path(store)
        for row in rows:
            data_list.append((kind, value) + row
                             + (context.get_relative_path(store),))

    data_headers = ('Identifier Type', 'Identifier', 'Title', 'Artist', 'Album',
                    'Album Artist', 'Genre', 'Composer', 'Duration (as stored)',
                    'Type (as stored)', 'Rating (as stored)', 'Track Number',
                    'Is Compilation (as stored)', 'Library Name', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
