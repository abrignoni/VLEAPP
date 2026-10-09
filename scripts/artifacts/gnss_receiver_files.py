"""GNSS receiver state files kept under a NAV/gnss folder.

Named for what the files are, not a vehicle: the samples behind this file come from a
Ford SYNC Gen3 module, whose GNSS receiver driver keeps its state in small binary files:

    NAV/gnss/GPSPosFile     a stored position
    NAV/gnss/GPS*File       GPS almanac, ephemeris, clock, ionosphere, UTC and oscillator state
    NAV/gnss/GLO*File       the same for GLONASS
    NAV/gnss/HlthFile       health state

Each non-empty file starts with the four bytes A5 A5 5A 5A and a 32-bit number, both
little-endian. No description of the layout was found; what is read here was worked out
from the files and is limited to that header and, in the position file, two numbers.
"""

import os
import struct
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor

__artifacts_v2__ = {
    "gnss_receiver_stored_position": {
        "name": "GNSS Receiver Files - Stored Position",
        "description": "The position stored in the GNSS receiver's position file, with the "
                       "time in the file's header.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GNSS Receiver Files",
        "notes": "From the state files a GNSS receiver driver keeps under NAV/gnss. Each "
                 "non-empty file starts with the bytes A5 A5 5A 5A and a 32-bit number. No "
                 "description of the layout was found; what is read was worked out from the "
                 "files. Tested on one unit, a 2018 Ford Expedition (SYNC Gen3) read from its "
                 "export. A tested Ford SYNC 4 logical zip has no such folder. The header "
                 "number is read as seconds since 1970 and written out with no offset applied: "
                 "read that way, ten of the twelve files fall on 2026-02-06 and two on "
                 "2026-03-20, which is the last day in the same unit's system manager log. "
                 "That agreement is the only check on the reading. This artifact reads "
                 "NAV/gnss/GPSPosFile, 76 bytes on the tested unit, and gave one row. Latitude "
                 "and longitude are the 32-bit numbers at offsets 28 and 32, read as a "
                 "fraction of a quarter turn and a half turn (the number times 90 or 180, "
                 "divided by 2 to the 31st). That scale was checked against the same unit: the "
                 "result lies within 0.01 degree of 4,674 of the 39,638 positions the Ford - "
                 "PAS Dev Loc Results artifact reads from its location log. The other numbers "
                 "in the file are not read. The row is the position the receiver had saved "
                 "when it wrote the file, which a receiver keeps to speed up its next fix. It "
                 "does not establish that the vehicle was at that place at the header time to "
                 "any stated accuracy.",
        "paths": ('*/NAV/gnss/GPSPosFile',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 1 "
                                       "row",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, no NAV/gnss folder",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
    "gnss_receiver_file_times": {
        "name": "GNSS Receiver Files - File Header Times",
        "description": "The header time of each GNSS receiver state file: almanac, ephemeris, "
                       "clock, ionosphere, UTC, oscillator, position and health files.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GNSS Receiver Files",
        "notes": "From the state files a GNSS receiver driver keeps under NAV/gnss. Each "
                 "non-empty file starts with the bytes A5 A5 5A 5A and a 32-bit number. No "
                 "description of the layout was found; what is read was worked out from the "
                 "files. Tested on one unit, a 2018 Ford Expedition (SYNC Gen3) read from its "
                 "export. A tested Ford SYNC 4 logical zip has no such folder. The header "
                 "number is read as seconds since 1970 and written out with no offset applied: "
                 "read that way, ten of the twelve files fall on 2026-02-06 and two on "
                 "2026-03-20, which is the last day in the same unit's system manager log. "
                 "That agreement is the only check on the reading. It gave 12 rows; two files "
                 "in the folder are empty and give none. Only the header is read. The contents "
                 "are satellite orbit and clock data the receiver downloaded or computed, not "
                 "a record of where the vehicle was. A row shows when the receiver last wrote "
                 "that file, which bounds when the receiver was running.",
        "paths": ('*/NAV/gnss/*File',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 12 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, no NAV/gnss folder",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
    },
}

_MAGIC = b'\xa5\xa5\x5a\x5a'
_LATITUDE_OFFSET = 28
_LONGITUDE_OFFSET = 32
_HALF_TURN = 2 ** 31


def _header_time(data):
    """The header's 32-bit number as seconds since 1970, or '' when the file is not one."""
    if len(data) < 8 or data[:4] != _MAGIC:
        return None
    seconds = struct.unpack('<I', data[4:8])[0]
    if not seconds:
        return ''
    return (datetime(1970, 1, 1) + timedelta(seconds=seconds)).strftime('%Y-%m-%d %H:%M:%S')


def _files(context):
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'rb') as handle:
                data = handle.read(4096)
        except OSError:
            continue
        yield file_found, data


@artifact_processor
def gnss_receiver_stored_position(context):
    data_list = []
    source_paths = []
    for file_found, data in _files(context):
        stamp = _header_time(data)
        if stamp is None or len(data) < _LONGITUDE_OFFSET + 4:
            continue
        latitude, longitude = struct.unpack('<ii', data[_LATITUDE_OFFSET:_LONGITUDE_OFFSET + 4])
        source_paths.append(file_found)
        data_list.append((stamp, latitude * 90 / _HALF_TURN, longitude * 180 / _HALF_TURN,
                          latitude, longitude, context.get_relative_path(file_found)))

    data_headers = (('Header Time', 'datetime'), 'Latitude', 'Longitude',
                    'Latitude (as stored)', 'Longitude (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gnss_receiver_file_times(context):
    data_list = []
    source_paths = []
    for file_found, data in _files(context):
        stamp = _header_time(data)
        if stamp is None:
            continue
        source_paths.append(file_found)
        data_list.append((stamp, os.path.basename(file_found),
                          struct.unpack('<I', data[4:8])[0], os.path.getsize(file_found),
                          context.get_relative_path(file_found)))

    data_headers = (('Header Time', 'datetime'), 'File', 'Header Number (as stored)',
                    'File Size', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
