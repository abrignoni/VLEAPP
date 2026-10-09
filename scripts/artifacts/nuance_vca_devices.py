"""Nuance VCA voice-control stores: the device table and the per-handset phonebooks.

Named for the voice-control component, not a vehicle: the stores sit under Nuance/VCA on
the head unit, and the samples behind this file are Ford SYNC units of two generations.
The NuanceVCAdb/Phone*.sqlite layout found on other units is read by nvcaContacts.py.

    Nuance/VCA/device.sqlite                 table T_Device
    Nuance/VCA/PhoneBook_<address>.sqlite    tables T_Person, T_Phone_Number
    Nuance/VCA/phone<address>_<n>_<lang>.sqlite   the same tables on SYNC Gen1v5
    Nuance/VCA/Media<n>_<lang>.sqlite        track, artist, album, playlist (Gen1v5)
    Nuance/VCA/media<n>.db                   the same plus mediacore_* and info (Gen2)
"""

import os
import re
import sqlite3

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "nuance_vca_devices": {
        "name": "Nuance VCA - Devices",
        "description": "Rows of the voice-control device table, with the device name and "
                       "Bluetooth address stored in each row and the type, media type and "
                       "status values as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From T_Device in Nuance/VCA/device.sqlite. Tested on three Ford SYNC units "
                 "read from their extracted file sets: a 2019 Ford Fusion (SYNC Gen1v5), a "
                 "2014 Ford Edge SEL and a 2011 Ford Explorer XLT (SYNC Gen2). They held 8, 2 "
                 "and 10 rows. The table has two layouts. The Gen2 units store the Bluetooth "
                 "address as an integer, shown here as twelve hex digits with colons; on the "
                 "Edge that value equalled the address in the name of the unit's call list and "
                 "phonebook files. The Gen1v5 unit stores it as twelve hex digits of text. A "
                 "zero or empty address is shown empty. One handset can have two rows with "
                 "different Device Type values. Device Type, Media Type, Active, Connection "
                 "Status and Source ID are shown as stored because nothing available here "
                 "documents their values. A row records that the voice-control component "
                 "listed the device. It does not establish who carried it.",
        "paths": ('*/Nuance/VCA/device.sqlite*',),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 8 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 2 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 10 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "nuance_vca_phonebook": {
        "name": "Nuance VCA - Handset Phonebook",
        "description": "Contacts in the voice-control phonebook database kept for each "
                       "handset, with the first name, last name, email, phone number and the "
                       "number type text the database stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From T_Person joined to T_Phone_Number and S_Phone_Number_Type in "
                 "Nuance/VCA/PhoneBook_<address>.sqlite and, on SYNC Gen1v5, "
                 "Nuance/VCA/phone<address>_<n>_<lang>.sqlite, which holds the same three "
                 "tables. Tested on three Ford SYNC units read from their extracted file sets: "
                 "a 2014 Ford Edge SEL and a 2011 Ford Explorer XLT (SYNC Gen2) and a 2019 "
                 "Ford Fusion (SYNC Gen1v5). Each held one such database, with 47, 7 and 108 "
                 "numbers. Handset Address is the twelve hex digits in the file name, shown "
                 "with colons. Number Type is the text the database's own type table gives for "
                 "the number. One row is one phone number, so a person with two numbers has "
                 "two rows. The Email column was empty on every tested row. A row records that "
                 "the voice-control component held the contact for that handset. It does not "
                 "establish that any number was dialled.",
        "paths": (
            '*/Nuance/VCA/PhoneBook_*.sqlite*',
            '*/Nuance/VCA/phone????????????_*.sqlite*',
        ),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 108 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 47 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 7 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "nuance_vca_media_library": {
        "name": "Nuance VCA - Media Library Entries",
        "description": "Track, artist, album and playlist names in the voice-control media "
                       "databases kept for each media source, with the source number from the "
                       "file name.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From Nuance/VCA/Media<n>_<lang>.sqlite (SYNC Gen1v5) and "
                 "Nuance/VCA/media<n>.db (SYNC Gen2), which the voice-control component keeps "
                 "so titles can be spoken. Tested on two Ford SYNC units read from their "
                 "extracted file sets. A 2019 Ford Fusion (Gen1v5) held four such databases "
                 "and gave 2,065 rows; a 2011 Ford Explorer XLT (Gen2) gave 6,915 rows from "
                 "one database, and a second database there has a damaged schema and is logged "
                 "and not read. The third tested unit, a 2014 Ford Edge SEL, had no media "
                 "database. Entry Kind says which table the row came from: track, artist, "
                 "album or playlist. On the Gen2 unit a track row carries the artist and album "
                 "its own columns link to (3,811 and 3,739 of 3,812 tracks); on the Gen1v5 "
                 "unit those link columns are empty, so the artist and album rows cannot be "
                 "tied to a track there. Genre and composer tables are not listed. Source ID "
                 "In File Name is the number in the file name; on both units every such number "
                 "is also a source id in the Devices artifact's table, which is the only tie "
                 "to a device found here. A row records that the component indexed the name "
                 "from a media source. It does not establish that the item was played.",
        "paths": ('*/Nuance/VCA/[Mm]edia[0-9]*',),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 2065 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "media database under Nuance/VCA",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 6915 "
                             "rows",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
    "nuance_vca_media_sources": {
        "name": "Nuance VCA - Media Source Info",
        "description": "The info row of a voice-control media database: the media source's "
                       "name, identifier, manufacturer, firmware and the item counts stored "
                       "for it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nuance VCA",
        "notes": "From the info table of Nuance/VCA/media<n>.db. Tested on three Ford SYNC "
                 "units read from their extracted file sets. Only the SYNC Gen2 layout has the "
                 "table: a 2011 Ford Explorer XLT gave one row, the SYNC Gen1v5 media "
                 "databases on a 2019 Ford Fusion have no info table, and a 2014 Ford Edge SEL "
                 "had no media database. On the one tested row the model and version columns "
                 "were empty and the others were filled. Unique ID and Protocol are shown as "
                 "stored; nothing available here documents them. The count columns are the "
                 "numbers the row stores, not counts made by this artifact. Source ID In File "
                 "Name is the number in the file name, as in the Media Library Entries "
                 "artifact.",
        "paths": ('*/Nuance/VCA/[Mm]edia[0-9]*',),
        "sample_data": {
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 0 rows, the "
                             "media databases have no info table",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "media database under Nuance/VCA",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_PHONEBOOK_NAME = re.compile(r'(?:PhoneBook_|phone)([0-9A-Fa-f]{12})(?:_\d+_\w+)?\.sqlite')


def _databases(context, wanted):
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        if not wanted(base) or base.endswith(('-journal', '-wal', '-shm')):
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
            yield file_found, db
        finally:
            db.close()


def _colons(digits):
    return ':'.join(digits[i:i + 2] for i in range(0, 12, 2)).lower()


def _address(value):
    """A stored Bluetooth address, integer or text, as aa:bb:cc:dd:ee:ff; '' when empty."""
    if isinstance(value, int):
        return _colons(f'{value:012x}') if 0 < value < 2 ** 48 else ''
    text = str(value or '').strip()
    if re.fullmatch(r'[0-9A-Fa-f]{12}', text):
        return _colons(text)
    return text


@artifact_processor
def nuance_vca_devices(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: name.startswith('device.sqlite')):
        try:
            cursor = db.execute('SELECT * FROM T_Device')
            columns = [item[0].lower() for item in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read T_Device: {ex}')
            continue
        source_paths.append(file_found)
        for row in rows:
            address = row.get('btaddress', row.get('bt_address'))
            source_id = row.get('src_id', row.get('device_source_id'))
            data_list.append((
                row.get('device_name') or '', _address(address), row.get('device_type'),
                row.get('media_type'), row.get('active_device'),
                row.get('connection_status'), source_id, row.get('t_device_id'),
                context.get_relative_path(file_found)))

    data_headers = ('Device Name', 'Bluetooth Address', 'Device Type (as stored)',
                    'Media Type (as stored)', 'Active (as stored)',
                    'Connection Status (as stored)', 'Source ID (as stored)', 'Row ID',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def nuance_vca_phonebook(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context,
                                     lambda name: _PHONEBOOK_NAME.match(name) is not None):
        try:
            rows = db.execute('''
                SELECT p.First_Name, p.Last_Name, p.Email, n.Phone_Number,
                       t.Phone_Number_Type
                FROM T_Phone_Number n
                LEFT JOIN T_Person p ON p.T_Person_id = n.T_Person_Id
                LEFT JOIN S_Phone_Number_Type t
                       ON t.S_Phone_Number_Type_id = n.S_Phone_Number_Type_Id
                ORDER BY n.T_Phone_Number_id''').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read the phonebook tables: {ex}')
            continue
        source_paths.append(file_found)
        address = _colons(_PHONEBOOK_NAME.match(os.path.basename(file_found)).group(1))
        for first, last, email, number, number_type in rows:
            data_list.append((address, first or '', last or '', email or '', number or '',
                              number_type or '', context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'First Name', 'Last Name', 'Email', 'Phone Number',
                    'Number Type', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

_MEDIA_NAME = re.compile(r'[Mm]edia(\d+)(?:_\w+)?\.(?:sqlite|db)$')


def _tables(db):
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(db, table):
    return {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}


def _named(db, table):
    """Rows of a name table, whichever of the two name columns the layout uses."""
    column = 'orthography' if 'orthography' in _columns(db, table) else 'name'
    return [row[0] for row in db.execute(f'SELECT "{column}" FROM "{table}" ORDER BY id')]


def _tracks(db):
    """(track name, artist, album) rows; artist and album only where the track links them."""
    columns = _columns(db, 'track')
    tables = _tables(db)
    if {'mediacore_artistid', 'mediacore_albumid'} <= columns and \
            {'mediacore_artist', 'mediacore_album'} <= tables:
        return db.execute('''
            SELECT t.name, r.name, a.name FROM track t
            LEFT JOIN mediacore_artist r ON r.id = t.mediacore_artistid
            LEFT JOIN mediacore_album a ON a.id = t.mediacore_albumid
            ORDER BY t.id''').fetchall()
    if {'artistId', 'albumId'} <= columns:
        return db.execute('''
            SELECT t.name, r.orthography, a.orthography FROM track t
            LEFT JOIN artist r ON r.id = t.artistId
            LEFT JOIN album a ON a.id = t.albumId
            ORDER BY t.id''').fetchall()
    return [(row[0], None, None) for row in db.execute('SELECT name FROM track ORDER BY id')]


@artifact_processor
def nuance_vca_media_library(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: _MEDIA_NAME.match(name) is not None):
        source_id = int(_MEDIA_NAME.match(os.path.basename(file_found)).group(1))
        relative = context.get_relative_path(file_found)
        before = len(data_list)
        try:
            tables = _tables(db)
            if 'track' in tables:
                for name, artist, album in _tracks(db):
                    data_list.append(('Track', name or '', artist or '', album or '',
                                      source_id, relative))
            for table, kind in (('artist', 'Artist'), ('album', 'Album'),
                                ('playlist', 'Playlist')):
                if table in tables:
                    for name in _named(db, table):
                        data_list.append((kind, name or '', '', '', source_id, relative))
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read the media tables of {relative}: {ex}')
            continue
        if len(data_list) > before:
            source_paths.append(file_found)

    data_headers = ('Entry Kind', 'Name', 'Artist', 'Album', 'Source ID In File Name',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


_INFO_COLUMNS = ('name', 'unique_id', 'manufacturer', 'model', 'version', 'firmware',
                 'protocol', 'titles', 'artists', 'albums', 'playlists', 'genres',
                 'composers', 'audiobooks', 'podcasts', 'videos', 'photos')


@artifact_processor
def nuance_vca_media_sources(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: _MEDIA_NAME.match(name) is not None):
        source_id = int(_MEDIA_NAME.match(os.path.basename(file_found)).group(1))
        relative = context.get_relative_path(file_found)
        try:
            if 'info' not in _tables(db):
                continue
            present = _columns(db, 'info')
            picked = ', '.join(f'"{column}"' if column in present else 'NULL'
                               for column in _INFO_COLUMNS)
            rows = db.execute(f'SELECT {picked} FROM info ORDER BY id').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Nuance VCA: could not read the info table of {relative}: {ex}')
            continue
        if rows:
            source_paths.append(file_found)
        for row in rows:
            data_list.append(tuple('' if value is None else value for value in row)
                             + (source_id, relative))

    data_headers = ('Name', 'Unique ID (as stored)', 'Manufacturer', 'Model', 'Version',
                    'Firmware', 'Protocol (as stored)', 'Titles', 'Artists', 'Albums',
                    'Playlists', 'Genres', 'Composers', 'Audiobooks', 'Podcasts', 'Videos',
                    'Photos', 'Source ID In File Name', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
