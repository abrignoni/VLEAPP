"""BMW NBT head unit: the navigation trail and trip stores under nav/.

Two SQLite stores sit in the navigation folder of the unit's second partition:

    nav/trails.sqlite   Trails   one row per trail, the positions in a Path blob
    nav/trips.sqlite    Trips    one row per trip, a Path blob in the same format

A Path blob is a six-byte header, a four-byte length (the blob's size less six), twelve
zero bytes, then tagged records, and the same length again in its last four bytes:

    tag (1 byte) | uint32 little-endian, rising along the trail | payload

The payload size is fixed per tag. Tags 0x1d and 0x1e carry a position, longitude then
latitude, each a signed 32-bit integer of 360 / 2**32 degree. Tag 0x02 carries a time, a
uint32 count of milliseconds after the row's own begin (or departure) time. Neither the
framing nor the tag meanings come from published documentation; they were worked out on
one unit and are checked here by the record grammar consuming every blob to its last byte.
"""

import os
import sqlite3
import struct
from datetime import datetime, timedelta, timezone

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "bmw_nbt_trail_points": {
        "name": "BMW NBT - Navigation Trail Points",
        "description": "Position records from the Path blob of each row in the navigation "
                       "store's Trails table, with the time each record is placed at, its "
                       "latitude and longitude, and the trail it belongs to.",
        "author": "@CyberMike81, Claude, OpenAI Codex",
        "creation_date": "2026-10-28",
        "last_update_date": "2026-10-29",
        "requirements": "none",
        "category": "BMW NBT",
        "notes": "Reads Trails.Path in nav/trails.sqlite. The record grammar was reverse engineered and tested "
                 "on one 2017 BMW 540i NBT unit; other units and software versions remain unverified. "
                 "Coordinates are signed 32-bit values times 360 / 2**32 degree. The stored integers are "
                 "retained because iVe uses a different divisor, 11,930,466. Timestamp is "
                 "BeginCoordinatedUniversalTime plus the first following time record's milliseconds. A position "
                 "after the final time record takes that time only when the blob is fully decoded. Missing time "
                 "records, undecodable pending times and zero or invalid base dates leave the time blank. Local "
                 "Time (as recorded) applies the same offset to BeginLocalTime without assigning a timezone. "
                 "Invalid latitude is blank while its stored integer is retained. Repeated positions are "
                 "retained. Record Tag (as stored) and Distance Along Trail (as stored) have no established "
                 "meaning or unit beyond their framing. No speed is reported. Other tags are framed but not "
                 "interpreted. Trip positions repeat trail positions in the tested unit and are summarized "
                 "separately. A position does not identify an occupant or driver.",
        "paths": ('*/nav/trails.sqlite*',),
        "sample_data": {
            "bmw_nbt_2017_540i_ive_logical": "2017 BMW 540i, NBT head unit, iVe logical file set "
                                        "| 265031 rows",
        },
        "output_types": "all",
        "artifact_icon": "navigation",
    },
    "bmw_nbt_trails": {
        "name": "BMW NBT - Navigation Trails",
        "description": "One row per row of the navigation store's Trails table: its begin and "
                       "end times, the DriverId, Length and DurationTime values the unit "
                       "stored, the number of position records in its Path blob, and its first "
                       "and last position.",
        "author": "@CyberMike81, Claude, OpenAI Codex",
        "creation_date": "2026-10-28",
        "last_update_date": "2026-10-29",
        "requirements": "none",
        "category": "BMW NBT",
        "notes": "One row per Trails record in nav/trails.sqlite. Begin Time and End Time are the stored UTC "
                 "Unix seconds; zero and invalid dates are blank. The local-time columns are the stored local "
                 "clock values without an assigned timezone. Driver ID (as stored) identifies a number, not a "
                 "person or a verified key. Length (as stored) and Duration (as stored) have no documented "
                 "units. Position Records counts decoded positions, including repeated positions. Path Decoded "
                 "reports framing failures and the offset/tag where parsing stopped; earlier positions are "
                 "retained, with unestablished times blank. Path Decoded was uniformly Yes in the tested real "
                 "unit. Valid and RoadNetworkRelation were uniform and are omitted; Bounding is not decoded. "
                 "Tested on one 2017 BMW 540i NBT unit. A trail does not identify an occupant or driver.",
        "paths": ('*/nav/trails.sqlite*',),
        "sample_data": {
            "bmw_nbt_2017_540i_ive_logical": "2017 BMW 540i, NBT head unit, iVe logical file set "
                                        "| 3772 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map",
    },
    "bmw_nbt_trips": {
        "name": "BMW NBT - Navigation Trips",
        "description": "One row per row of the navigation store's Trips table: its departure "
                       "and arrival times, the DriverIds, Length and DurationTime values the "
                       "unit stored, the number of position records in its Path blob, and its "
                       "first and last position.",
        "author": "@CyberMike81, Claude, OpenAI Codex",
        "creation_date": "2026-10-28",
        "last_update_date": "2026-10-29",
        "requirements": "none",
        "category": "BMW NBT",
        "notes": "Reads Trips in nav/trips.sqlite. Departure Time and Arrival Time are stored UTC Unix seconds; "
                 "zero and invalid dates are blank. Local-time columns have no assigned timezone. Driver IDs (as "
                 "stored) decodes the count-prefixed integer list, falling back to hex for an unrecognized blob; "
                 "the numbers do not identify a person or verified key. Length (as stored) and Duration (as "
                 "stored) have no documented units. Path Decoded was uniformly Yes in the tested real unit; "
                 "failures name the stopping offset/tag. Trip positions duplicate trail positions in that unit, "
                 "so only their count and first/last positions appear here. Source, Mode, RoadNetworkRelation "
                 "and Valid were uniform and are omitted. BackwardReferences, Locations, Parameters, Bounding, "
                 "CountryCodes, BmwAdasStreetTypes and RoadClasses are not interpreted. The sibling Trails table "
                 "has no times or positions; LinkToTripIndexTiles was empty. Tested on one 2017 BMW 540i NBT "
                 "unit. A trip does not identify an occupant or driver.",
        "paths": ('*/nav/trips.sqlite*',),
        "sample_data": {
            "bmw_nbt_2017_540i_ive_logical": "2017 BMW 540i, NBT head unit, iVe logical file set "
                                        "| 650 rows",
        },
        "output_types": "standard",
        "artifact_icon": "truck",
    },
}

# Payload size of each record type, after its tag byte and four-byte rising value.
_PAYLOAD = {0x02: 4, 0x03: 12, 0x07: 2, 0x14: 0, 0x15: 4, 0x16: 0, 0x17: 2, 0x18: 1,
            0x1d: 8, 0x1e: 8, 0x1f: 4, 0x20: 1, 0x22: 1, 0x23: 3, 0x24: 1}
_POSITION_TAGS = (0x1d, 0x1e)
_TIME_TAG = 0x02
_HEADER = 22
_MAGIC = b'\x0a\x01\x01\x00\x01\x00'
_UNITS = 360 / 2 ** 32


def _degrees(value):
    return round(value * _UNITS, 8)


def _latitude(value):
    degrees = _degrees(value)
    return degrees if -90 <= degrees <= 90 else ''


def _utc(seconds, milliseconds=0):
    if seconds in (None, 0, '') or milliseconds is None:
        return ''
    try:
        return datetime.fromtimestamp(seconds, timezone.utc) + timedelta(milliseconds=milliseconds)
    except (OverflowError, OSError, TypeError, ValueError):
        return ''


def _as_recorded(seconds, milliseconds=0):
    """A stored epoch value written out as text, with no zone applied."""
    stamp = _utc(seconds, milliseconds)
    return stamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if stamp else ''


def _decode_path(blob):
    """Positions in a Path blob, each timed by the next time record.

    Returns ([(record index, tag, rising value, longitude, latitude, milliseconds)],
    'Yes' or a note saying where the grammar stopped).
    """
    if not isinstance(blob, bytes) or len(blob) < _HEADER + 4:
        return [], 'No: blob shorter than the header'
    if blob[:6] != _MAGIC or blob[10:_HEADER] != bytes(12):
        return [], 'No: unsupported blob header'
    if struct.unpack_from('<I', blob, 6)[0] != len(blob) - 6:
        return [], 'No: length field does not match the blob size'
    positions = []
    pending = []
    last_time = None
    offset, end, index = _HEADER, len(blob) - 4, 0
    status = 'Yes'
    while offset < end:
        tag = blob[offset]
        size = _PAYLOAD.get(tag)
        if size is None or offset + 5 + size > end:
            status = f'No: stopped at offset {offset}, tag 0x{tag:02x}'
            break
        rising = struct.unpack_from('<I', blob, offset + 1)[0]
        if tag in _POSITION_TAGS:
            longitude, latitude = struct.unpack_from('<ii', blob, offset + 5)
            pending.append([index, tag, rising, longitude, latitude, None])
        elif tag == _TIME_TAG:
            last_time = struct.unpack_from('<I', blob, offset + 5)[0]
            for position in pending:
                position[5] = last_time
            positions.extend(pending)
            pending = []
        offset += 5 + size
        index += 1
    if status == 'Yes' and offset != end:
        status = f'No: records overran the blob at offset {offset}'
    if status == 'Yes' and struct.unpack_from('<I', blob, end)[0] != len(blob) - 6:
        status = 'No: trailing length does not match the blob size'
    for position in pending:
        position[5] = last_time if status == 'Yes' else None
    positions.extend(pending)
    if status == 'Yes' and positions and last_time is None:
        status = 'No: positions have no time record'
    return [tuple(position) for position in positions], status


def _source_paths(context, name):
    return sorted({str(path) for path in context.get_files_found()
                   if os.path.normcase(os.path.basename(str(path))) == os.path.normcase(name)})


def _stores(context, name):
    """Each matched store with the given file name, opened read-only."""
    for file_found in _source_paths(context, name):
        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        yield file_found, db


def _trail_rows(context):
    """(source file, trail row, decoded positions, status) for every trail."""
    for file_found, db in _stores(context, 'trails.sqlite'):
        try:
            cursor = db.execute(
                'SELECT TrailId, DriverId, Length, BeginCoordinatedUniversalTime, '
                'EndCoordinatedUniversalTime, BeginLocalTime, EndLocalTime, DurationTime, Path '
                'FROM Trails ORDER BY BeginCoordinatedUniversalTime, TrailId')
            rows = cursor.fetchall()
        except sqlite3.Error as ex:
            logfunc(f'BMW NBT trails: {os.path.basename(file_found)} not read: {ex}')
            db.close()
            continue
        db.close()
        undecoded = 0
        for row in rows:
            positions, status = _decode_path(row[8])
            if status != 'Yes':
                undecoded += 1
                logfunc(f'BMW NBT trails: trail {row[0]} Path not fully decoded ({status})')
            yield file_found, row, positions, status
        logfunc(f'BMW NBT trails: {len(rows)} trails in {os.path.basename(file_found)}, '
                f'{undecoded} not fully decoded')


@artifact_processor
def bmw_nbt_trail_points(context):
    data_list = []
    source_paths = _source_paths(context, 'trails.sqlite')
    for file_found, row, positions, _status in _trail_rows(context):
        relative = context.get_relative_path(file_found)
        trail_id, begin_utc, begin_local = row[0], row[3], row[5]
        for index, tag, rising, longitude, latitude, milliseconds in positions:
            data_list.append((_utc(begin_utc, milliseconds),
                              _as_recorded(begin_local, milliseconds),
                              _latitude(latitude), _degrees(longitude), trail_id, index,
                              f'0x{tag:02x}', rising, latitude, longitude, relative))

    data_headers = (('Timestamp', 'datetime'), 'Local Time (as recorded)', 'Latitude',
                    'Longitude', 'Trail ID', 'Record Index', 'Record Tag (as stored)',
                    'Distance Along Trail (as stored)', 'Latitude (as stored)',
                    'Longitude (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def bmw_nbt_trails(context):
    data_list = []
    source_paths = _source_paths(context, 'trails.sqlite')
    for file_found, row, positions, status in _trail_rows(context):
        trail_id, driver_id, length, begin_utc, end_utc, begin_local, end_local, duration, _ = row
        first = positions[0] if positions else None
        last = positions[-1] if positions else None
        data_list.append((_utc(begin_utc), _utc(end_utc), _as_recorded(begin_local),
                          _as_recorded(end_local), trail_id, driver_id, length, duration,
                          len(positions),
                          _latitude(first[4]) if first else '', _degrees(first[3]) if first else '',
                          _latitude(last[4]) if last else '', _degrees(last[3]) if last else '',
                          status, context.get_relative_path(file_found)))

    data_headers = (('Begin Time', 'datetime'), ('End Time', 'datetime'), 'Begin Local Time',
                    'End Local Time', 'Trail ID', 'Driver ID (as stored)', 'Length (as stored)',
                    'Duration (as stored)', 'Position Records', 'First Latitude',
                    'First Longitude', 'Last Latitude', 'Last Longitude', 'Path Decoded',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _driver_ids(blob):
    """The DriverIds blob as a uint32 count and that many uint32 values, or as stored."""
    if not isinstance(blob, bytes):
        return ''
    if len(blob) >= 4:
        count = struct.unpack_from('<I', blob, 0)[0]
        if len(blob) == 4 + 4 * count:
            return ', '.join(str(value) for value in struct.unpack_from(f'<{count}I', blob, 4))
    return blob.hex()


@artifact_processor
def bmw_nbt_trips(context):
    data_list = []
    source_paths = _source_paths(context, 'trips.sqlite')
    for file_found, db in _stores(context, 'trips.sqlite'):
        try:
            rows = db.execute(
                'SELECT TripId, DriverIds, Length, DepartureCoordinatedUniversalTime, '
                'ArrivalCoordinatedUniversalTime, DepartureLocalTime, ArrivalLocalTime, '
                'DurationTime, Path FROM Trips '
                'ORDER BY DepartureCoordinatedUniversalTime, TripId').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'BMW NBT trips: {os.path.basename(file_found)} not read: {ex}')
            db.close()
            continue
        db.close()
        relative = context.get_relative_path(file_found)
        undecoded = 0
        for trip_id, driver_ids, length, dep_utc, arr_utc, dep_local, arr_local, duration, path in rows:
            positions, status = _decode_path(path)
            if status != 'Yes':
                undecoded += 1
                logfunc(f'BMW NBT trips: trip {trip_id} Path not fully decoded ({status})')
            first = positions[0] if positions else None
            last = positions[-1] if positions else None
            data_list.append((_utc(dep_utc), _utc(arr_utc), _as_recorded(dep_local),
                              _as_recorded(arr_local), trip_id, _driver_ids(driver_ids), length,
                              duration, len(positions),
                              _latitude(first[4]) if first else '',
                              _degrees(first[3]) if first else '',
                              _latitude(last[4]) if last else '', _degrees(last[3]) if last else '',
                              status, relative))
        logfunc(f'BMW NBT trips: {len(rows)} trips in {os.path.basename(file_found)}, '
                f'{undecoded} not fully decoded')

    data_headers = (('Departure Time', 'datetime'), ('Arrival Time', 'datetime'),
                    'Departure Local Time', 'Arrival Local Time', 'Trip ID',
                    'Driver IDs (as stored)', 'Length (as stored)', 'Duration (as stored)',
                    'Position Records', 'First Latitude', 'First Longitude', 'Last Latitude',
                    'Last Longitude', 'Path Decoded', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
