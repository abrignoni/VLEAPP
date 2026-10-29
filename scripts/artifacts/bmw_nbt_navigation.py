"""BMW NBT head unit: the navigation trail and trip stores under nav/.

Two SQLite stores sit in the navigation folder of the unit's second partition:

    nav/trails.sqlite   Trails   one row per trail, the positions in a Path blob
    nav/trips.sqlite    Trips    one row per trip, a Path blob in the same format

A Path blob is a six-byte header, a four-byte length (the blob's size less six), twelve
zero bytes, then tagged records, and the same length again in its last four bytes:

    tag (1 byte) | uint32 little-endian, rising along the trail | payload

The supported framing and tag interpretations were inferred on one 2017 BMW 540i NBT
unit, not from published documentation. Tags 0x1d and 0x1e are interpreted as longitude
then latitude, each a signed 32-bit integer scaled by 360 / 2**32 degree. Tag 0x02 is
interpreted as a uint32 millisecond offset from the row's begin (or departure) time.
Only a following time record supplies a position's offset. Positions after the final
time record remain untimed even when the record grammar consumes the whole blob.
"""

import os
import sqlite3
import struct
from datetime import datetime, timedelta, timezone

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "bmw_nbt_trail_points": {
        "name": "BMW NBT - Navigation Trail Points",
        "description": "Position records from the navigation store's Trails.Path blobs, with "
                       "coordinates, trail identifiers and inferred times where a following "
                       "time record is available.",
        "author": "@CyberMike81, Claude, OpenAI Codex",
        "creation_date": "2026-10-28",
        "last_update_date": "2026-10-29",
        "requirements": "none",
        "category": "BMW NBT",
        "notes": "The format was worked out on one 2017 BMW 540i NBT unit. Coordinate scaling is inferred as "
                 "signed 32-bit values times 360 / 2**32 degree; stored integers remain available for comparison "
                 "with other tools. BeginCoordinatedUniversalTime is inferred as Unix seconds UTC, and time "
                 "records as millisecond offsets. Timestamp uses the first following time record; positions "
                 "after the final time record remain untimed. Local Time (no zone) derives from BeginLocalTime "
                 "and the same offset, without an assigned timezone. Zero/invalid dates and unestablished times "
                 "are blank. Rising Value (as stored) is the uint32 before the payload; its meaning and unit are "
                 "unestablished. Repeated positions remain; invalid latitude is blank. Other tags are framed but "
                 "not interpreted. No speed or occupant/driver identity is inferred.",
        "paths": ('*/nav/trails.sqlite*',),
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
        "notes": "The format and coordinate scaling (signed 32-bit values times 360 / 2**32 degree) were "
                 "inferred on one 2017 BMW 540i NBT unit. Begin Time and End Time interpret "
                 "BeginCoordinatedUniversalTime and EndCoordinatedUniversalTime as Unix seconds UTC; that "
                 "interpretation is inferred. Local-time columns have no assigned timezone. Zero/invalid dates "
                 "are blank. Driver ID (as stored) is an identifier, not a verified key or person. Length (as "
                 "stored) and Duration (as stored) have no established units. Position Records counts decoded "
                 "positions, including repeats. Path Decoded reports framing or missing-time-record problems; "
                 "decoded positions are retained. Valid, RoadNetworkRelation and Bounding are not interpreted or "
                 "reported.",
        "paths": ('*/nav/trails.sqlite*',),
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
        "notes": "The format and coordinate scaling (signed 32-bit values times 360 / 2**32 degree) were "
                 "inferred on one 2017 BMW 540i NBT unit. Departure Time and Arrival Time interpret "
                 "DepartureCoordinatedUniversalTime and ArrivalCoordinatedUniversalTime as Unix seconds UTC; "
                 "that interpretation is inferred. Local-time columns have no assigned timezone. Zero/invalid "
                 "dates are blank. Driver IDs uses an inferred count-prefixed uint32 list; unrecognized blobs "
                 "are shown as hex. The IDs do not identify a verified key or person. Length (as stored) and "
                 "Duration (as stored) have no established units. Trip paths supply the position count and "
                 "first/last coordinates; individual trip positions are not reported. Path Decoded reports "
                 "framing or missing-time-record problems. Other trip fields and auxiliary tables are not "
                 "interpreted.",
        "paths": ('*/nav/trips.sqlite*',),
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
    """Render inferred seconds plus an offset as clock text with no assigned zone."""
    stamp = _utc(seconds, milliseconds)
    return stamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if stamp else ''


def _decode_path(blob):
    """Positions in a Path blob, timed only when a following time record is decoded.

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

    data_headers = (('Timestamp', 'datetime'), 'Local Time (no zone)', 'Latitude',
                    'Longitude', 'Trail ID', 'Record Index', 'Record Tag (as stored)',
                    'Rising Value (as stored)', 'Latitude (as stored)',
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
    """Interpret an inferred count-prefixed ID list, keeping unrecognized blobs as hex."""
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
                    'Driver IDs', 'Length (as stored)', 'Duration (as stored)',
                    'Position Records', 'First Latitude', 'First Longitude', 'Last Latitude',
                    'Last Longitude', 'Path Decoded', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
