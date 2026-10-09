"""QNX multimedia sync databases: the media library a head unit builds for each device.

Named for the component, not a vehicle: a database of this kind carries an _mmsync_info_
table, and the samples behind this file come from a Ford SYNC Gen3 module, which keeps
one per connected media device:

    storage/bk<n>/Media<kind>_<n>.db     SQLite: files, audio_metadata, artists, albums,
                                         genres, playlists, playlist_entries,
                                         mediastore_metadata

A file is read only when it is a SQLite database that has the _mmsync_info_ table. Times
are stored as whole numbers of nanoseconds since 1970 and record no time zone.
"""

import os
import sqlite3
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "qnx_mmsync_media_stores": {
        "name": "QNX Media Sync - Media Stores",
        "description": "One row for each media sync database: the store type and mount path, "
                       "the device identifier it carries, when it was last synced, the first "
                       "and last time a file was added and the number of files and playlists.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "QNX Media Sync",
        "notes": "From storage/bk<n>/Media<kind>_<n>.db, the library database a QNX head unit "
                 "builds for each media device it has synced; a file is read only when it is a "
                 "SQLite database with the _mmsync_info_ table. Tested on one unit, a 2018 "
                 "Ford Expedition (SYNC Gen3) read from its export, which held eight such "
                 "databases, all of the iAP2 kind (MediaiAP2_<n>.db). A tested GM GA-130 unit "
                 "and a tested Ford SYNC 4 logical zip have no such file. Times are whole "
                 "numbers of nanoseconds since 1970 with no time zone; they are the unit's "
                 "clock, written out as if UTC with no offset applied. The eight rows have "
                 "last sync times from 2021-11 to 2023-08 and from 0 to 12,771 files. Store "
                 "Type Name was ipodiap2 on all eight and Store Name was empty on all eight. "
                 "Device ID is the device_id value of the schema table, as stored; the eight "
                 "values are all different, and what the identifier is derived from is not "
                 "established here. Mount Path is the path the unit mounted the device at, one "
                 "of two on the tested unit. The device names and serial numbers are in the "
                 "unit's separate media service database, which the Ford - Media Service "
                 "artifact reads. A row records that the unit synced a media library from a "
                 "device at that time. It does not establish whose device it was.",
        "paths": ('*/bk[0-9]*/Media*.db',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 8 "
                                       "rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 0 rows, no "
                             "media sync database",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, no media sync database",
        },
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    },
    "qnx_mmsync_files": {
        "name": "QNX Media Sync - Media Files",
        "description": "Files in each media sync database with the artist, album and genre its "
                       "metadata links to, the year and track number, and the time the file "
                       "was added to the database.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "QNX Media Sync",
        "notes": "From storage/bk<n>/Media<kind>_<n>.db, the library database a QNX head unit "
                 "builds for each media device it has synced; a file is read only when it is a "
                 "SQLite database with the _mmsync_info_ table. Tested on one unit, a 2018 "
                 "Ford Expedition (SYNC Gen3) read from its export, which held eight such "
                 "databases, all of the iAP2 kind (MediaiAP2_<n>.db). A tested GM GA-130 unit "
                 "and a tested Ford SYNC 4 logical zip have no such file. Times are whole "
                 "numbers of nanoseconds since 1970 with no time zone; they are the unit's "
                 "clock, written out as if UTC with no offset applied. It gave 43,064 rows "
                 "from seven of the eight databases; the eighth holds no file. File Name is "
                 "the files table's filename, which on the tested iAP2 stores is a title with "
                 "no folder path. Artist, album and genre come from joining the file's audio "
                 "metadata to the name tables, and all 43,064 rows carried an artist and an "
                 "album. Date Added is when the unit added the file to its database, from "
                 "2021-10-18 to 2023-08-07 on the tested unit, and it clusters at each sync; "
                 "it is not when the file was put on the device. The database also holds "
                 "phonetic and identifier tables for voice control, which are not listed. A "
                 "row records that the unit indexed that item from a device. It does not "
                 "establish that the item was played.",
        "paths": ('*/bk[0-9]*/Media*.db',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | "
                                       "43064 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 0 rows, no "
                             "media sync database",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, no media sync database",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
    "qnx_mmsync_playlists": {
        "name": "QNX Media Sync - Playlists",
        "description": "Playlists in each media sync database with the name, the number of "
                       "entries and the modified time the database stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "QNX Media Sync",
        "notes": "From storage/bk<n>/Media<kind>_<n>.db, the library database a QNX head unit "
                 "builds for each media device it has synced; a file is read only when it is a "
                 "SQLite database with the _mmsync_info_ table. Tested on one unit, a 2018 "
                 "Ford Expedition (SYNC Gen3) read from its export, which held eight such "
                 "databases, all of the iAP2 kind (MediaiAP2_<n>.db). A tested GM GA-130 unit "
                 "and a tested Ford SYNC 4 logical zip have no such file. Times are whole "
                 "numbers of nanoseconds since 1970 with no time zone; they are the unit's "
                 "clock, written out as if UTC with no offset applied. It gave 281 rows "
                 "holding 74,172 entries between them; every row carried a name and a modified "
                 "time. Entries is the number of rows in the playlist entries table for that "
                 "playlist; the entries themselves are not listed and can be read from the "
                 "database by the playlist id. Date Modified is the value the unit stored for "
                 "the playlist, and whether it comes from the device or from the sync is not "
                 "established here. A row records that the unit indexed that playlist from a "
                 "device.",
        "paths": ('*/bk[0-9]*/Media*.db',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | "
                                       "281 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 0 rows, no "
                             "media sync database",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, no media sync database",
        },
        "output_types": "standard",
        "artifact_icon": "list",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_EPOCH = datetime(1970, 1, 1)


def _time(value):
    """Nanoseconds since 1970 as text; '' when zero, not a number or out of range."""
    if not isinstance(value, int) or value <= 0:
        return ''
    try:
        return (_EPOCH + timedelta(microseconds=value // 1000)).strftime('%Y-%m-%d %H:%M:%S')
    except OverflowError:
        return ''


def _text(value):
    return '' if value is None else value


def _databases(context):
    """(path, relative path, connection) for each matched database with _mmsync_info_."""
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'rb') as handle:
                if handle.read(16) != _SQLITE_MAGIC:
                    continue
        except OSError:
            continue
        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        try:
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if '_mmsync_info_' in tables:
                yield file_found, context.get_relative_path(file_found), db
        except sqlite3.Error as ex:
            logfunc(f'QNX media sync: could not read {os.path.basename(file_found)}: {ex}')
        finally:
            db.close()


def _one(db, query):
    try:
        return db.execute(query).fetchone()
    except sqlite3.Error:
        return None


@artifact_processor
def qnx_mmsync_media_stores(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _databases(context):
        store = _one(db, 'SELECT last_sync, mssname, name, mountpath FROM mediastore_metadata')
        schema = _one(db, 'SELECT version, device_id, locale FROM _dbschema_info_')
        files = _one(db, 'SELECT count(*), min(date_added), max(date_added) FROM files')
        playlists = _one(db, 'SELECT count(*) FROM playlists')
        if store is None and files is None:
            continue
        store = store or (None, None, None, None)
        schema = schema or (None, None, None)
        files = files or (0, None, None)
        source_paths.append(file_found)
        data_list.append((_time(store[0]), _time(files[1]), _time(files[2]),
                          _text(store[1]), _text(store[2]), _text(store[3]),
                          _text(schema[1]), files[0], playlists[0] if playlists else 0,
                          _text(schema[0]), _text(schema[2]), relative))

    data_headers = (('Last Sync', 'datetime'), ('First File Added', 'datetime'),
                    ('Last File Added', 'datetime'), 'Store Type Name', 'Store Name',
                    'Mount Path', 'Device ID (as stored)', 'Files', 'Playlists',
                    'Schema Version', 'Locale', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def qnx_mmsync_files(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _databases(context):
        try:
            rows = db.execute('''
                SELECT f.date_added, f.filename, r.artist, b.album, g.genre, a.year, a.track,
                       f.size, f.fid
                FROM files f
                LEFT JOIN audio_metadata a ON a.fid = f.fid
                LEFT JOIN artists r ON r.artist_id = a.artist_id
                LEFT JOIN albums b ON b.album_id = a.album_id
                LEFT JOIN genres g ON g.genre_id = a.genre_id
                ORDER BY f.fid''').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'QNX media sync: could not read the file tables of {relative}: {ex}')
            continue
        if rows:
            source_paths.append(file_found)
        for added, name, artist, album, genre, year, track, size, fid in rows:
            data_list.append((_time(added), _text(name), _text(artist), _text(album),
                              _text(genre), _text(year), _text(track), _text(size), fid,
                              relative))

    data_headers = (('Date Added', 'datetime'), 'File Name', 'Artist', 'Album', 'Genre',
                    'Year', 'Track', 'Size (as stored)', 'File ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def qnx_mmsync_playlists(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _databases(context):
        try:
            rows = db.execute('''
                SELECT p.date_modified, p.name, p.filename,
                       (SELECT count(*) FROM playlist_entries e WHERE e.plid = p.plid), p.plid
                FROM playlists p ORDER BY p.plid''').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'QNX media sync: could not read the playlist tables of {relative}: {ex}')
            continue
        if rows:
            source_paths.append(file_found)
        for modified, name, filename, entries, plid in rows:
            data_list.append((_time(modified), _text(name), _text(filename), entries, plid,
                              relative))

    data_headers = (('Date Modified', 'datetime'), 'Playlist Name', 'File Name', 'Entries',
                    'Playlist ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
