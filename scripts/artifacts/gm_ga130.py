"""GM GA-130 infotainment radio.

Named for the module: the same radio is fitted across GM models, and the samples behind
this file are a Chevrolet Equinox and a Chevrolet Malibu. Its user data partition holds:

    storage/NPS/BT_MID/phonebook           Bluetooth phonebooks and call lists, SQLite
    HMI_DB/pasa_addressbook_data<n>.db     one address book per number, SQLite
    storage/bk<n>/mme                      the media engine database, SQLite
    logs/sys_error.log.<n>                 a timestamped system log

The phonebook and address book files are stored as zlib streams that inflate to SQLite
databases. This module inflates them in memory, writes the result to its own temporary
file and reads that; the evidence file is only read. An acquisition can also hold an
already inflated copy of the same file, so identical databases are read once.
"""

import hashlib
import os
import re
import sqlite3
import tempfile
import zlib
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "gm_ga130_phonebook": {
        "name": "GM GA-130 - Bluetooth Phonebook",
        "description": "Contacts in the radio's numbered Bluetooth phonebook tables, with the "
                       "sort name, first and last name, the phone numbers and their stored "
                       "types, and the postal address the row carries.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
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
                 "numbers; 1, 2, 4 and 64 occur and nothing available here documents them. A "
                 "row records that the radio held the contact. It does not establish that any "
                 "number was dialled.",
        "paths": ('*/storage/NPS/BT_MID/phonebook*',),
        "sample_data": {
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 0 rows, the "
                             "PhoneBook tables held no rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 741 rows",
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
        for table in tables:
            for row in _rows(db, table):
                numbers = []
                types = []
                for index in range(9):
                    number = _text(row.get(f'TelNum{index}')).strip()
                    if number:
                        numbers.append(number)
                        types.append(_text(row.get(f'TelType{index}')))
                address = ', '.join(part for part in (
                    _text(row.get(key)).strip() for key in
                    ('POBox', 'ExtendAdr', 'StreetAdr', 'Locality', 'Region', 'POCode',
                     'Country')) if part)
                data_list.append((
                    int(table[len('PhoneBook'):]), _text(row.get('SortName')),
                    _text(row.get('FirstName')), _text(row.get('LastName')),
                    '; '.join(numbers), '; '.join(types), address, row.get('RecId'),
                    context.get_relative_path(file_found)))

    data_headers = ('Table Number', 'Sort Name', 'First Name', 'Last Name', 'Phone Numbers',
                    'Number Types (as stored)', 'Address', 'Record ID', 'Source File')
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
