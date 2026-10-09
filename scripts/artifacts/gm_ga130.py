"""GM GA-130 infotainment radio.

Named for the module: the same radio is fitted across GM models, and the samples behind
this file are a Chevrolet Equinox and a Chevrolet Malibu. Its user data partition holds:

    storage/NPS/BT_MID/phonebook           Bluetooth phonebooks and call lists, SQLite
    HMI_DB/pasa_addressbook_data<n>.db     one address book per number, SQLite
    HMI_DB/pasa_media_data<n>.db           song, artist and album names per number, SQLite
    storage/bk<n>/mme                      the media engine database, SQLite
    logs/sys_error.log.<n>                 a timestamped system log

The phonebook also gives the PhoneBook records still on its freelist pages.

The phonebook and address book files are stored as zlib streams that inflate to SQLite
databases. This module inflates them in memory, writes the result to its own temporary
file and reads that; the evidence file is only read. An acquisition can also hold an
already inflated copy of the same file, so identical databases are read once.
"""

import hashlib
import os
import re
import sqlite3
import struct
import tempfile
import zlib
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "gm_ga130_phonebook": {
        "name": "GM GA-130 - Bluetooth Phonebook",
        "description": "Contacts in the radio's numbered Bluetooth phonebook tables and on the "
                       "database's freelist pages, with the sort name, first and last name, "
                       "the phone numbers and their stored types, the postal address the row "
                       "carries, and whether the row is a table row or a freelist row.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From the PhoneBook1 to PhoneBook5 tables of storage/NPS/BT_MID/phonebook. "
                 "Tested on two units, a 2014 Chevrolet Equinox LT and a 2015 Chevrolet "
                 "Malibu, read from the file sets extracted from each unit's storage. The file "
                 "is stored as a zlib stream that inflates to a SQLite database; it is "
                 "inflated in memory and read from a temporary copy, and the evidence file is "
                 "not changed. An extraction that also holds an already inflated copy of the "
                 "same database has it read once. The Malibu held 741 contacts in tables 2 and "
                 "4. The Equinox held the same tables with no rows. Table Number is the number "
                 "in the table name; that each number is one paired handset is the natural "
                 "reading and is not established here, and the database holds no device name "
                 "or address. Number Types are the TelType values in the same order as the "
                 "numbers; 1, 2, 4 and 64 occur and nothing available here documents them. "
                 "Record Source is 'table row' for a row the SQLite library returns and "
                 "'freelist page N' for a record read from a table leaf page the database has "
                 "released to its freelist, which the library does not return. A freelist "
                 "record is reported when it has the PhoneBook tables' 31 columns, with text "
                 "and integers where those columns store them, carries a name or a number, and "
                 "its reported fields differ from every table row and every freelist row "
                 "already reported. Which PhoneBook table a freelist row came from is not "
                 "recorded, so Table Number is empty on those rows, and their Record ID is the "
                 "key the row had on that page. On the Malibu 28 freelist leaf pages held "
                 "1,131 records: 710 repeat a table row, 2 repeat another freelist row and 419 "
                 "are reported, from 21 pages. All 419 carry a sort name and a number; 4 have "
                 "the sort name of a table row. The text of an independent parse of that unit "
                 "holds a number of 737 of the 738 table rows that carry one of seven or more "
                 "digits, and of 23 of the 419 freelist rows, so the freelist rows are not "
                 "confirmed by a second reader. "
                 "Freelist cells that continue on overflow pages are not read; none was left "
                 "out here. The Equinox database had no freelist pages. A row records that the "
                 "radio held the contact, and a freelist row that the database once held that "
                 "row; when it was removed is not recorded. Neither establishes that any "
                 "number was dialled.",
        "paths": ('*/storage/NPS/BT_MID/phonebook*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 0 rows, the "
                             "PhoneBook tables held no rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 1160 rows, "
                             "741 table rows and 419 freelist rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "gm_ga130_call_history": {
        "name": "GM GA-130 - Bluetooth Call History",
        "description": "Rows of the radio's numbered received, dialled and missed call tables, "
                       "with the call clock reading, the name and number the row carries, and "
                       "which table it came from.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From the InCall, DialCall and MissCall tables, numbered 1 to 5, of "
                 "storage/NPS/BT_MID/phonebook. Tested on two units, a 2014 Chevrolet Equinox "
                 "LT and a 2015 Chevrolet Malibu, read from the file sets extracted from each "
                 "unit's storage. The file is stored as a zlib stream that inflates to a "
                 "SQLite database; it is inflated in memory and read from a temporary copy, "
                 "and the evidence file is not changed. An extraction that also holds an "
                 "already inflated copy of the same database has it read once. Call List is "
                 "taken from the table name: InCall is shown as Received, DialCall as Dialled "
                 "and MissCall as Missed. The Malibu held 147 rows, all but two in the tables "
                 "numbered 2. The Equinox held the same tables with no rows. Call Time is "
                 "assembled from the six date and time text columns each row stores. The store "
                 "records no time zone, so the time is the unit's clock reading, written out "
                 "as if it were UTC with no offset applied. Table Number is the number in the "
                 "table name; that each number is one paired handset is not established here. "
                 "Number Type is TelType as stored. A row records that the radio held this "
                 "call list entry. It does not establish who used the handset.",
        "paths": ('*/storage/NPS/BT_MID/phonebook*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 0 rows, the "
                             "call tables held no rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 147 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "gm_ga130_address_book": {
        "name": "GM GA-130 - Address Book",
        "description": "Entries of the radio's numbered address book databases, with the name, "
                       "the cell, home, work and other phone numbers and the postal address "
                       "each entry carries.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From the name table of HMI_DB/pasa_addressbook_data1.db to "
                 "pasa_addressbook_data5.db. Tested on two units, a 2014 Chevrolet Equinox LT "
                 "and a 2015 Chevrolet Malibu, read from the file sets extracted from each "
                 "unit's storage. The file is stored as a zlib stream that inflates to a "
                 "SQLite database; it is inflated in memory and read from a temporary copy, "
                 "and the evidence file is not changed. An extraction that also holds an "
                 "already inflated copy of the same database has it read once. Both units held "
                 "all five files, with 1,623 entries on the Malibu and 437 on the Equinox. "
                 "File Number is the number in the file name. On the Malibu files 3 and 4 held "
                 "721 and 724 entries and Bluetooth phonebook tables 2 and 4 held 17 and 724 "
                 "contacts, so the two numberings are not the same one, and which handset a "
                 "file belongs to is not established here. The address columns were empty on "
                 "every tested entry of the Malibu. An entry records that the radio held the "
                 "name and numbers. It does not establish that any number was dialled. The "
                 "pasa_media_data databases beside these files index media titles and are not "
                 "read.",
        "paths": ('*/HMI_DB/pasa_addressbook_data*.db*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 437 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 1623 rows",
        },
        "output_types": "standard",
        "artifact_icon": "users",
    },
    "gm_ga130_media_stores": {
        "name": "GM GA-130 - Media Stores",
        "description": "Rows of the media engine's media store table: the phones, players and "
                       "USB storage the radio registered, with the name and identifier of each "
                       "and the last seen and last sync times.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From the mediastores table of storage/bk1/mme and storage/bk2/mme, plain "
                 "SQLite databases. Tested on two units, a 2014 Chevrolet Equinox LT and a "
                 "2015 Chevrolet Malibu, read from the file sets extracted from each unit's "
                 "storage. The two files are not copies of each other: on both units they held "
                 "different rows, so both are read and Source File says which. The Malibu gave "
                 "207 rows and the Equinox 378. Last Seen and Last Sync are the stored "
                 "integers read as nanoseconds since 1970 and shown as UTC. That unit is "
                 "derived from the data: read that way the values fall between 2014 and 2020 "
                 "on these 2014 and 2015 vehicles, and two rows on each unit hold a value of a "
                 "few seconds or zero, which is shown only in Last Seen (as stored). For the "
                 "ipod and mediafs kinds the Identifier held a non-empty string on every "
                 "tested row. Store Kind is the mssname column and Storage Type is shown as "
                 "stored; most rows were kind devb. The track library in the same database "
                 "lists the contents of the attached media and is not surfaced. A row records "
                 "that the radio registered the store. It does not establish what was played.",
        "paths": ('*/storage/bk*/mme*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 378 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 207 rows",
        },
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    },
    "gm_ga130_played_media": {
        "name": "GM GA-130 - Played Media",
        "description": "Tracks in the media engine's library that carry a last played time or "
                       "a play count, with the title, file name, the media store they belong "
                       "to and those values.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From the library table of storage/bk1/mme and storage/bk2/mme, joined to "
                 "mediastores on msid for the store's name and identifier. Tested on two units "
                 "read from their extracted file sets, a 2014 Chevrolet Equinox LT and a 2015 "
                 "Chevrolet Malibu, which gave 31 and 120 rows. Only rows whose last_played or "
                 "fullplay_count is above zero are reported; the rest of the library, tens of "
                 "thousands of rows listing the contents of attached media, is not. Last "
                 "Played is the stored integer read as nanoseconds since 1970 and shown as "
                 "UTC, the same reading the Media Stores artifact derives for its times; on "
                 "these rows it fell between 2014 and 2020. Every tested row carried a last "
                 "played time and a title, and 48 rows on the Malibu carried a play count. "
                 "Full Play Count and Duration are shown as stored. File Name was empty on 70 "
                 "of the 151 tested rows. The database names a text collation this tool does "
                 "not have, so a plain one is registered on the temporary copy to let the "
                 "title column be read; it does not change the stored values. The two database "
                 "files hold different rows and both are read. A row records that the media "
                 "engine stamped the track as played at that time. It does not establish who "
                 "chose it.",
        "paths": ('*/storage/bk*/mme*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 31 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 120 rows",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
    "gm_ga130_system_events": {
        "name": "GM GA-130 - System Log Shutdowns",
        "description": "Shutdown lines from the radio's system log, with the log time of each "
                       "'Shutdown Received' and 'Emergency Shutdown received' line.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From logs/sys_error.log.0 and sys_error.log.1. Tested on two units, a 2014 "
                 "Chevrolet Equinox LT and a 2015 Chevrolet Malibu, read from the file sets "
                 "extracted from each unit's storage. Each line starts with a date and time in "
                 "angle brackets. The date is read month first: across both units a value "
                 "above 12 occurs 913 times in the second position and never in the first. The "
                 "store records no time zone, so the time is the unit's clock reading, written "
                 "out as if it were UTC with no offset applied. Many lines carry a 1970 date, "
                 "written before the unit's clock was set; those are left out and counted in "
                 "the run log, because the reading is an uptime and not a date. Every 'New "
                 "Boot Cycle' line on both units carried a 1970 date, so boots are not listed. "
                 "The rows that remain number 145 on the Malibu and 177 on the Equinox. The "
                 "other messages in the log are internal status lines and are not surfaced. A "
                 "row records that the radio logged a shutdown at that clock reading. What "
                 "caused it is not established.",
        "paths": ('*/logs/sys_error.log*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 177 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 145 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "gm_ga130_media_index": {
        "name": "GM GA-130 - Media Name Index",
        "description": "Song names with the artist, album and genre the index links them to, "
                       "and playlist names, from the radio's numbered media name databases.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM GA-130",
        "notes": "From HMI_DB/pasa_media_data<n>.db, stored as a zlib stream that inflates to "
                 "a SQLite database; an already inflated copy with the same content is read "
                 "once. Tested on two units read from their extracted file sets, a 2014 "
                 "Chevrolet Equinox LT and a 2015 Chevrolet Malibu, which held two such "
                 "databases each and gave 2,356 and 2,700 rows. A Song row is one distinct "
                 "combination of song, artist, album and genre from the main table joined to "
                 "the name tables; 2,302 of 2,302 and 2,679 of 2,679 song rows carried an "
                 "artist. A Playlist row is a name from the playlist table, and which songs a "
                 "playlist holds is not surfaced. The databases also hold phonetic "
                 "transcription tables for the names, which are not listed. What the file "
                 "number stands for is not established here; the radio keeps numbered address "
                 "book files the same way. The index holds no time. A row records that the "
                 "radio indexed the name from a media source. It does not establish that the "
                 "item was played; the Played Media artifact reads the media engine's own "
                 "record of that.",
        "paths": ('*/HMI_DB/pasa_media_data*.db*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 2356 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 2700 rows",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
# The call list tables name their own direction.
_CALL_TABLES = (('InCall', 'Received'), ('DialCall', 'Dialled'), ('MissCall', 'Missed'))
_LOG_LINE = re.compile(r'^<(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)>/(.*)$')
_LOG_EVENTS = ('Shutdown Received', 'Emergency Shutdown received')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _database_bytes(path):
    """The SQLite database a file holds, inflating it when it is a zlib stream.

    Returns None for anything that is neither a database nor a stream of one.
    """
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except OSError:
        return None
    if data.startswith(_SQLITE_MAGIC):
        return data
    try:
        inflated = zlib.decompress(data)
    except zlib.error:
        return None
    return inflated if inflated.startswith(_SQLITE_MAGIC) else None


def _databases(context, wanted):
    """Yield (source path, connection) once per distinct database among matched files.

    A file stored as a zlib stream sorts before its '(uncompressed)' copy, so the stream
    is the one named as the source. The connection is to a temporary copy owned by this
    module, removed when the caller moves on.
    """
    seen = set()
    for file_found in _regular_files(context):
        if not wanted(os.path.basename(file_found)):
            continue
        data = _database_bytes(file_found)
        if data is None:
            continue
        digest = hashlib.sha256(data).digest()
        if digest in seen:
            continue
        seen.add(digest)
        handle, temp_path = tempfile.mkstemp(suffix='.db')
        try:
            with os.fdopen(handle, 'wb') as temp:
                temp.write(data)
            try:
                db = sqlite3.connect(f'file:{temp_path}?mode=ro', uri=True)
                # The media engine database names a collation this build does not have.
                db.create_collation('cldr', lambda x, y: (x > y) - (x < y))
            except sqlite3.Error:
                continue
            try:
                yield file_found, db
            finally:
                db.close()
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _tables(db):
    try:
        return {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.Error:
        return set()


def _rows(db, table):
    """Rows of a table as dicts; a table that cannot be read gives none and is logged."""
    try:
        cursor = db.execute(f'SELECT * FROM "{table}"')
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except sqlite3.Error as ex:
        logfunc(f'GM GA-130: could not read {table}: {ex}')
        return []


def _text(value):
    return '' if value is None else str(value)


def _is_phonebook(name):
    return name.startswith('phonebook')


# ---------------------------------------------------------------------------
# SQLite freelist leaf pages
# ---------------------------------------------------------------------------

def _varint(data, offset):
    value = 0
    for i in range(9):
        byte = data[offset + i]
        if i == 8:
            return (value << 8) | byte, offset + 9
        value = (value << 7) | (byte & 0x7f)
        if not byte & 0x80:
            return value, offset + i + 1
    raise ValueError('varint')


def _decode_record(payload):
    header_len, offset = _varint(payload, 0)
    if header_len > len(payload):
        raise ValueError('header')
    serials = []
    while offset < header_len:
        serial, offset = _varint(payload, offset)
        serials.append(serial)
    values = []
    pos = header_len
    for serial in serials:
        if serial == 0:
            values.append(None)
        elif 1 <= serial <= 6:
            size = (1, 2, 3, 4, 6, 8)[serial - 1]
            values.append(int.from_bytes(payload[pos:pos + size], 'big', signed=True))
            pos += size
        elif serial == 7:
            values.append(struct.unpack('>d', payload[pos:pos + 8])[0])
            pos += 8
        elif serial in (8, 9):
            values.append(serial - 8)
        elif serial >= 12 and serial % 2 == 0:
            size = (serial - 12) // 2
            values.append(payload[pos:pos + size])
            pos += size
        elif serial >= 13:
            size = (serial - 13) // 2
            values.append(payload[pos:pos + size].decode('utf-8', 'replace'))
            pos += size
        else:
            raise ValueError('serial type')
    if pos != len(payload):
        raise ValueError('record length')
    return values


def _freelist_rows(data):
    """Records on freelist pages that are still intact table leaf pages.

    Takes the bytes of a database. Returns (rows, skipped) where rows is a list of
    (page number, rowid, values) and skipped counts cells left out because they continue
    onto overflow pages or do not decode. Follows the freelist trunk chain from the
    database header; a page is read only when its first byte is the table-leaf type.
    Text is decoded as UTF-8, so a database in another encoding gives nothing.
    """
    rows = []
    skipped = 0
    if len(data) < 100 or data[:16] != _SQLITE_MAGIC:
        return rows, skipped
    if struct.unpack('>I', data[56:60])[0] != 1:
        return rows, skipped
    page_size = struct.unpack('>H', data[16:18])[0]
    if page_size == 1:
        page_size = 65536
    if page_size < 512:
        return rows, skipped
    usable = page_size - data[20]
    page_count = len(data) // page_size
    trunk = struct.unpack('>I', data[32:36])[0]

    free_pages = []
    seen = set()
    while trunk and trunk not in seen and trunk <= page_count:
        seen.add(trunk)
        start = (trunk - 1) * page_size
        next_trunk, leaf_count = struct.unpack('>II', data[start:start + 8])
        if leaf_count > (usable - 8) // 4:
            break
        free_pages.append(trunk)
        free_pages.extend(struct.unpack(f'>{leaf_count}I',
                                        data[start + 8:start + 8 + 4 * leaf_count]))
        trunk = next_trunk

    max_local = usable - 35
    for page in free_pages:
        if not 1 < page <= page_count:
            continue
        start = (page - 1) * page_size
        if data[start] != 0x0d:
            continue
        cell_count = struct.unpack('>H', data[start + 3:start + 5])[0]
        if 8 + 2 * cell_count > page_size:
            continue
        for index in range(cell_count):
            pointer = struct.unpack('>H', data[start + 8 + 2 * index:
                                               start + 10 + 2 * index])[0]
            try:
                payload_len, offset = _varint(data, start + pointer)
                rowid, offset = _varint(data, offset)
                if payload_len > max_local or offset + payload_len > start + page_size:
                    skipped += 1
                    continue
                rows.append((page, rowid,
                             _decode_record(data[offset:offset + payload_len])))
            except (ValueError, IndexError, struct.error):
                skipped += 1
    return rows, skipped


def _table_columns(db, table):
    try:
        return [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
    except sqlite3.Error:
        return []


def _contact(row):
    """The reported fields of a PhoneBook row given as a dict of its columns."""
    numbers = []
    types = []
    for index in range(9):
        number = _text(row.get(f'TelNum{index}')).strip()
        if number:
            numbers.append(number)
            types.append(_text(row.get(f'TelType{index}')))
    address = ', '.join(part for part in (
        _text(row.get(key)).strip() for key in
        ('POBox', 'ExtendAdr', 'StreetAdr', 'Locality', 'Region', 'POCode', 'Country'))
        if part)
    return (_text(row.get('SortName')), _text(row.get('FirstName')),
            _text(row.get('LastName')), '; '.join(numbers), '; '.join(types), address)


def _freelist_contacts(data, columns):
    """((page, rowid, row dict) list, cells left out) for freelist records that have the
    PhoneBook tables' column count and store text and integers where those columns do."""
    found = []
    rows, left_out = _freelist_rows(data)
    for page, rowid, values in rows:
        row = dict(zip(columns, values))
        fits = len(values) == len(columns) and all(
            isinstance(row[name], int) if name.startswith('TelType') or name == 'SortNameId'
            else row[name] is None or isinstance(row[name], str)
            for name in columns if name != 'RecId')
        if fits:
            found.append((page, rowid, row))
        else:
            left_out += 1
    return found, left_out


# ---------------------------------------------------------------------------
# Bluetooth phonebook and call lists
# ---------------------------------------------------------------------------

@artifact_processor
def gm_ga130_phonebook(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, _is_phonebook):
        tables = sorted(name for name in _tables(db) if re.fullmatch(r'PhoneBook\d+', name))
        if not tables:
            continue
        source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        current = set()
        for table in tables:
            for row in _rows(db, table):
                contact = _contact(row)
                current.add(contact)
                data_list.append((int(table[len('PhoneBook'):]),) + contact + (
                    row.get('RecId'), 'table row', relative))

        # Rows of earlier states that are still on the database's freelist pages.
        layouts = {tuple(_table_columns(db, table)) for table in tables}
        data = _database_bytes(file_found)
        if len(layouts) != 1 or data is None:
            logfunc(f'GM GA-130 phonebook: freelist of {os.path.basename(file_found)} not '
                    'read, the PhoneBook tables do not share one column layout or the file '
                    'could not be read again')
            continue
        found, left_out = _freelist_contacts(data, list(layouts.pop()))
        recovered = 0
        for page, rowid, row in found:
            contact = _contact(row)
            if contact in current or not any(contact[:4]):
                continue
            current.add(contact)
            recovered += 1
            data_list.append(('',) + contact + (rowid, f'freelist page {page}', relative))
        logfunc(f'GM GA-130 phonebook: {len(found)} freelist records, {recovered} reported, '
                f'{left_out} freelist cells left out in {os.path.basename(file_found)}')

    data_headers = ('Table Number', 'Sort Name', 'First Name', 'Last Name', 'Phone Numbers',
                    'Number Types (as stored)', 'Address', 'Record ID', 'Record Source',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _call_time(row):
    parts = [_text(row.get(key)).strip() for key in
             ('Date_YYYY', 'Date_MM', 'Date_DD', 'Time_hh', 'Time_min', 'Time_sec')]
    if not all(part.isdigit() for part in parts):
        return ''
    try:
        return datetime(*(int(part) for part in parts)).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


@artifact_processor
def gm_ga130_call_history(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, _is_phonebook):
        names = _tables(db)
        found = False
        for prefix, label in _CALL_TABLES:
            for table in sorted(name for name in names
                                if re.fullmatch(prefix + r'\d+', name)):
                found = True
                for row in _rows(db, table):
                    data_list.append((
                        _call_time(row), label, _text(row.get('SortName')),
                        _text(row.get('TelNum')), row.get('TelType'),
                        int(table[len(prefix):]), row.get('RecId'), table,
                        context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Name', 'Phone Number',
                    'Number Type (as stored)', 'Table Number', 'Record ID', 'Table',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Address book
# ---------------------------------------------------------------------------

@artifact_processor
def gm_ga130_address_book(context):
    data_list = []
    source_paths = []

    def wanted(name):
        return re.match(r'pasa_addressbook_data\d+\.db', name) is not None

    for file_found, db in _databases(context, wanted):
        if 'name' not in _tables(db):
            continue
        source_paths.append(file_found)
        number = int(re.match(r'pasa_addressbook_data(\d+)\.db',
                              os.path.basename(file_found)).group(1))
        for row in _rows(db, 'name'):
            phones = '; '.join(
                f'{label}: {_text(row.get(key)).strip()}' for key, label in
                (('phoneCell', 'Cell'), ('phoneHome', 'Home'), ('phoneWork', 'Work'),
                 ('phoneOther', 'Other')) if _text(row.get(key)).strip())
            address = ', '.join(part for part in (
                _text(row.get(key)).strip() for key in
                ('streetAddress', 'locality', 'region', 'postalCode', 'countryName'))
                                if part)
            data_list.append((number, _text(row.get('name')), phones, address,
                              row.get('nameId'), context.get_relative_path(file_found)))

    data_headers = ('File Number', 'Name', 'Phone Numbers', 'Address', 'Name ID',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Media stores
# ---------------------------------------------------------------------------

def _nanoseconds(value):
    """An integer count of nanoseconds since 1970 as 'YYYY-MM-DD HH:MM:SS', or ''.

    Values below one year's worth are an uptime, not a date, and give ''.
    """
    if not isinstance(value, int) or value < 31536000 * 10**9:
        return ''
    try:
        return datetime.fromtimestamp(value / 1e9, tz=timezone.utc).strftime(
            '%Y-%m-%d %H:%M:%S')
    except (ValueError, OverflowError, OSError):
        return ''


@artifact_processor
def gm_ga130_media_stores(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: name.startswith('mme')):
        if 'mediastores' not in _tables(db):
            continue
        source_paths.append(file_found)
        for row in _rows(db, 'mediastores'):
            data_list.append((
                _nanoseconds(row.get('lastseen')), _nanoseconds(row.get('last_sync')),
                _text(row.get('name')), _text(row.get('identifier')),
                _text(row.get('mssname')), row.get('storage_type'),
                _text(row.get('mountpath')), row.get('lastseen'), row.get('msid'),
                context.get_relative_path(file_found)))

    data_headers = (('Last Seen', 'datetime'), ('Last Sync', 'datetime'), 'Name',
                    'Identifier', 'Store Kind', 'Storage Type (as stored)', 'Mount Path',
                    'Last Seen (as stored)', 'Media Store ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

@artifact_processor
def gm_ga130_played_media(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: name.startswith('mme')):
        names = _tables(db)
        if 'library' not in names:
            continue
        stores = {row.get('msid'): row for row in _rows(db, 'mediastores')} \
            if 'mediastores' in names else {}
        try:
            rows = db.execute(
                'SELECT last_played, title, filename, fullplay_count, duration, msid, fid '
                'FROM library WHERE last_played > 0 OR fullplay_count > 0').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'GM GA-130: could not read library: {ex}')
            continue
        source_paths.append(file_found)
        for last_played, title, filename, plays, duration, msid, fid in rows:
            store = stores.get(msid, {})
            data_list.append((
                _nanoseconds(last_played), _text(title), _text(filename), plays, duration,
                _text(store.get('name')), _text(store.get('identifier')), msid, fid,
                context.get_relative_path(file_found)))

    data_headers = (('Last Played', 'datetime'), 'Title', 'File Name', 'Full Play Count',
                    'Duration (as stored)', 'Media Store Name', 'Media Store Identifier',
                    'Media Store ID', 'Library ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# System log
# ---------------------------------------------------------------------------

@artifact_processor
def gm_ga130_system_events(context):
    data_list = []
    source_paths = []
    seen = set()
    for file_found in _regular_files(context):
        if not os.path.basename(file_found).startswith('sys_error.log'):
            continue
        try:
            with open(file_found, 'rb') as handle:
                data = handle.read()
        except OSError:
            continue
        digest = hashlib.sha256(data).digest()
        if digest in seen:
            continue
        seen.add(digest)
        found = False
        unset = 0
        for number, line in enumerate(data.decode('utf-8', 'replace').splitlines(), start=1):
            match = _LOG_LINE.match(line)
            if not match or match.group(8).strip() not in _LOG_EVENTS:
                continue
            month, day, year, hour, minute, second = (int(v) for v in match.groups()[:6])
            if year == 1970:
                # The unit's clock had not been set: the reading is an uptime, not a date.
                unset += 1
                continue
            try:
                stamp = datetime(year, month, day, hour, minute,
                                 second).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
            found = True
            data_list.append((stamp, match.group(8).strip(), number,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)
        logfunc(f'GM GA-130: {unset} shutdown lines with a 1970 clock left out of '
                f'{os.path.basename(file_found)}')

    data_headers = (('Log Time', 'datetime'), 'Event', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

@artifact_processor
def gm_ga130_media_index(context):
    data_list = []
    source_paths = []

    def wanted(name):
        return re.match(r'pasa_media_data\d+\.db', name) is not None

    for file_found, db in _databases(context, wanted):
        if not {'main', 'song', 'artist', 'album'} <= set(_tables(db)):
            continue
        number = int(re.match(r'pasa_media_data(\d+)\.db',
                              os.path.basename(file_found)).group(1))
        relative = context.get_relative_path(file_found)
        before = len(data_list)
        try:
            songs = db.execute('''
                SELECT DISTINCT s.songname, a.artistname, b.albumname, g.genrename
                FROM main m
                JOIN song s ON s.songId = m.songId
                LEFT JOIN artist a ON a.artistId = m.artistId
                LEFT JOIN album b ON b.albumId = m.albumId
                LEFT JOIN genre g ON g.genreId = m.genreId
                ORDER BY s.rowid''').fetchall()
            playlists = db.execute(
                'SELECT playlistname FROM playlist ORDER BY rowid').fetchall() \
                if 'playlist' in _tables(db) else []
        except sqlite3.Error as ex:
            logfunc(f'GM GA-130: could not read the media index tables: {ex}')
            continue
        for song, artist, album, genre in songs:
            data_list.append(('Song', _text(song), _text(artist), _text(album),
                              _text(genre), number, relative))
        for (playlist,) in playlists:
            data_list.append(('Playlist', _text(playlist), '', '', '', number, relative))
        if len(data_list) > before:
            source_paths.append(file_found)

    data_headers = ('Entry Kind', 'Name', 'Artist', 'Album', 'Genre', 'File Number',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
