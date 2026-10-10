"""GM OnStar telematics module: navigation data read from a raw flash image.

Some OnStar acquisitions carry only the module's flash image, with no file system a tool
can walk. The Continental-built generation 8 module is the case this was written for.
The image still holds the navigation component's own records in the clear:

    position records   20 bytes each, written one per second in long runs
    log lines          time-stamped text, among them destinations and guidance prompts

The same records are present in the image of an LG-built generation 9 module, where the
live copies are also read as files by gm_onstar_lg.py. The image holds more of them
than the files do, because it keeps blocks the file system has already released.

Nothing here follows a file system. Position records are found by scanning, so a
record is kept only when it stands in a run of at least five consecutive valid records;
an image with no navigation data gives a handful of chance matches and no runs.
"""

import bisect
import os
import re
import struct
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "gm_onstar_flash_gps_track": {
        "name": "GM OnStar Flash Image - GPS Track",
        "description": "Position records found in a GM OnStar module's raw flash image, one "
                       "per second, with the time, latitude, longitude, speed and heading of "
                       "each record.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "GM OnStar Flash Image",
        "notes": "Read from the module's raw flash image, matched as "
                 "LargeOutputFiles/image.bin inside an acquisition folder or given on its own "
                 "with the single-file input type. Tested on seven images: three "
                 "Continental-built generation 8 modules (2010 and 2011 Cadillac CTS, 16 MiB "
                 "each) and four LG-built generation 9 modules (2012 Chevrolet Cruze LT, 2012 "
                 "GMC Acadia, 2014 GMC Sierra 1500 SLE and 2011 Buick Enclave, 64 MiB each). "
                 "The three Cadillac images and the Acadia image held navigation data; the "
                 "other three held none and gave no rows. A position record is 20 big-endian "
                 "bytes: latitude and longitude as integers of 1/6,000,000 degree, month, day, "
                 "year, a speed value, a heading value, then hour, minute and second. No file "
                 "system is followed. Candidates are located by the year field and tested as "
                 "whole records, and a record is reported only when it stands in a run of at "
                 "least five valid records exactly 20 bytes apart. That rule is what separates "
                 "data from chance: the three images with no navigation data gave 14 or 15 "
                 "isolated candidates each and no runs, and the Cadillac images gave 3 to 8 "
                 "isolated candidates beside about 12,580 records in runs. On the Acadia 1,916 "
                 "candidates in shorter chains were left out. The counts are written to the "
                 "run log. The decoding was checked by comparison with an independent parse of "
                 "each unit: on the three Cadillac images 37,654 timestamps were common to "
                 "both and the position agreed on every one to within 0.000002 degree; on the "
                 "Acadia it agreed on 30,454 of 30,462. Speed is the stored value read as "
                 "millimetres per second and Heading is the upper nine bits of the heading "
                 "value; both readings were derived on the generation 9 module's live file and "
                 "are carried over to generation 8, where speeds up to 133 km/h and headings "
                 "from 0 to 359 are consistent with them but were not separately checked. The "
                 "data states no time zone. An independent parse of the same units labels "
                 "these times UTC, and that is not established here by other means, so the "
                 "time is written out as stored with no offset applied. The image can hold the "
                 "same item more than once; it is reported once, with Times Found, and Image "
                 "Offset is where it was first read. Run Length is the number of records in "
                 "the run the row belongs to. A record states where the module's receiver "
                 "placed itself at that time. It does not establish who was in the vehicle. "
                 "The three tested generation 8 images (xtrmp_item033, xtrmp_item034 and "
                 "xtrmp_item035) each hold about 2,400 stretches of about 40 to 54 bytes, most "
                 "46 to 52, in which one two-byte value repeats, about 0.7 percent of the "
                 "image. About 9 in 10 are 4,100 to 4,400 bytes from the next, some about "
                 "twice that, at positions that differ per image. In a 2.5 MiB range of "
                 "firmware the three units share (offsets 0x20000 to 0x2A0000), of the 608 "
                 "stretches one image has, 596 fall where a second image has no stretch, and "
                 "in all 596 the second image holds no repeated value; 98 percent of the bytes "
                 "that differ between two images in that range lie in those stretches. They "
                 "are not content the units share, and their even spacing at offsets that "
                 "differ per image is consistent with a fault in how the flash was read. Each "
                 "unit was read once, so that is not established, and neither is the cause. "
                 "One 64-byte stretch per image is the same in all three and is stored "
                 "content. Crosses Repeated Stretch says Yes when the bytes of a row's record "
                 "or line overlap such a stretch (40 bytes or more of one repeated two-byte "
                 "value whose two bytes differ). A record a stretch crosses can be cut, lost, "
                 "or reported with changed values: 30, 21 and 26 reported records in the three "
                 "images say Yes, and a position that jumps away from its neighbours should be "
                 "checked against that column and Image Offset. No row of the tested "
                 "generation 9 image says Yes.",
        "paths": ('*/LargeOutputFiles/image.bin',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9 (LG), flash image | 0 rows, "
                             "no run of position records in the image",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9 (LG), flash image | 30554 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9 (LG), flash image | 0 "
                             "rows, no run of position records in the image",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9 (LG), flash image | 0 rows, no "
                             "run of position records in the image",
            "xtrmp_item033": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | "
                             "12580 rows",
            "xtrmp_item034": "2010 Cadillac CTS, OnStar Gen8 (Continental), flash image | "
                             "12578 rows",
            "xtrmp_item035": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | "
                             "12582 rows",
        },
        "output_types": "all",
        "artifact_icon": "navigation",
    },
    "gm_onstar_flash_nav_destinations": {
        "name": "GM OnStar Flash Image - Navigation Destinations",
        "description": "Navigation destination lines found in a GM OnStar module's raw flash "
                       "image, with the log time and the latitude and longitude each line "
                       "states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "GM OnStar Flash Image",
        "notes": "Read from the module's raw flash image, matched as "
                 "LargeOutputFiles/image.bin inside an acquisition folder or given on its own "
                 "with the single-file input type. Tested on seven images: three "
                 "Continental-built generation 8 modules (2010 and 2011 Cadillac CTS, 16 MiB "
                 "each) and four LG-built generation 9 modules (2012 Chevrolet Cruze LT, 2012 "
                 "GMC Acadia, 2014 GMC Sierra 1500 SLE and 2011 Buick Enclave, 64 MiB each). "
                 "The three Cadillac images and the Acadia image held navigation data; the "
                 "other three held none and gave no rows. A destination line is time-stamped "
                 "log text of the form 'Dest lat <integer> lon <integer> "
                 "(<degrees>,<degrees>)'. Lines are found by that whole pattern, not by "
                 "following a file system. Latitude and Longitude are the parenthesised values "
                 "and the integers are kept in the as-stored columns. The three Cadillac "
                 "images gave 21, 21 and 22 distinct destinations, the same number an "
                 "independent parse listed for each, and the Acadia gave 38 against its 41. "
                 "The data states no time zone. An independent parse of the same units labels "
                 "these times UTC, and that is not established here by other means, so the "
                 "time is written out as stored with no offset applied. The image can hold the "
                 "same item more than once; it is reported once, with Times Found, and Image "
                 "Offset is where it was first read. A row records that the module logged a "
                 "route to that destination at that time. It does not establish that the "
                 "vehicle arrived there. The three tested generation 8 images (xtrmp_item033, "
                 "xtrmp_item034 and xtrmp_item035) each hold about 2,400 stretches of about 40 "
                 "to 54 bytes, most 46 to 52, in which one two-byte value repeats, about 0.7 "
                 "percent of the image. About 9 in 10 are 4,100 to 4,400 bytes from the next, "
                 "some about twice that, at positions that differ per image. In a 2.5 MiB "
                 "range of firmware the three units share (offsets 0x20000 to 0x2A0000), of "
                 "the 608 stretches one image has, 596 fall where a second image has no "
                 "stretch, and in all 596 the second image holds no repeated value; 98 percent "
                 "of the bytes that differ between two images in that range lie in those "
                 "stretches. They are not content the units share, and their even spacing at "
                 "offsets that differ per image is consistent with a fault in how the flash "
                 "was read. Each unit was read once, so that is not established, and neither "
                 "is the cause. One 64-byte stretch per image is the same in all three and is "
                 "stored content. Crosses Repeated Stretch says Yes when the bytes of a row's "
                 "record or line overlap such a stretch (40 bytes or more of one repeated "
                 "two-byte value whose two bytes differ). A line a stretch crosses can be cut "
                 "or lost. No reported row in the tested images says Yes.",
        "paths": ('*/LargeOutputFiles/image.bin',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9 (LG), flash image | 0 rows, "
                             "no destination line in the image",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9 (LG), flash image | 38 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9 (LG), flash image | 0 "
                             "rows, no destination line in the image",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9 (LG), flash image | 0 rows, no "
                             "destination line in the image",
            "xtrmp_item033": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | 21 "
                             "rows",
            "xtrmp_item034": "2010 Cadillac CTS, OnStar Gen8 (Continental), flash image | 21 "
                             "rows",
            "xtrmp_item035": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | 22 "
                             "rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "gm_onstar_flash_nav_guidance": {
        "name": "GM OnStar Flash Image - Navigation Guidance Prompts",
        "description": "Turn-by-turn guidance prompt lines found in a GM OnStar module's raw "
                       "flash image, with the log time, the maneuver, the street named and the "
                       "distance text of each prompt.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "GM OnStar Flash Image",
        "notes": "Read from the module's raw flash image, matched as "
                 "LargeOutputFiles/image.bin inside an acquisition folder or given on its own "
                 "with the single-file input type. Tested on seven images: three "
                 "Continental-built generation 8 modules (2010 and 2011 Cadillac CTS, 16 MiB "
                 "each) and four LG-built generation 9 modules (2012 Chevrolet Cruze LT, 2012 "
                 "GMC Acadia, 2014 GMC Sierra 1500 SLE and 2011 Buick Enclave, 64 MiB each). "
                 "The three Cadillac images and the Acadia image held navigation data; the "
                 "other three held none and gave no rows. A prompt line is time-stamped log "
                 "text beginning 'VIAMOTOSendHMIData audio', followed by prompt codes, a "
                 "maneuver, the word street, a street name and a distance. Lines are found by "
                 "that whole pattern, not by following a file system. Generation 8 writes the "
                 "street after 'street ' and generation 9 after 'street :'; both are read, and "
                 "%20 is shown as a space. The three Cadillac images gave 241, 265 and 257 "
                 "prompts and the Acadia 362. The numeric prompt codes are not surfaced. A "
                 "line cut short by the end of a flash block is reported as far as it reads. "
                 "The data states no time zone. An independent parse of the same units labels "
                 "these times UTC, and that is not established here by other means, so the "
                 "time is written out as stored with no offset applied. The image can hold the "
                 "same item more than once; it is reported once, with Times Found, and Image "
                 "Offset is where it was first read. A row records that the module issued that "
                 "prompt. It names a street on the planned route and does not by itself place "
                 "the vehicle on it; the GPS Track artifact holds the positions. The three "
                 "tested generation 8 images (xtrmp_item033, xtrmp_item034 and xtrmp_item035) "
                 "each hold about 2,400 stretches of about 40 to 54 bytes, most 46 to 52, in "
                 "which one two-byte value repeats, about 0.7 percent of the image. About 9 in "
                 "10 are 4,100 to 4,400 bytes from the next, some about twice that, at "
                 "positions that differ per image. In a 2.5 MiB range of firmware the three "
                 "units share (offsets 0x20000 to 0x2A0000), of the 608 stretches one image "
                 "has, 596 fall where a second image has no stretch, and in all 596 the second "
                 "image holds no repeated value; 98 percent of the bytes that differ between "
                 "two images in that range lie in those stretches. They are not content the "
                 "units share, and their even spacing at offsets that differ per image is "
                 "consistent with a fault in how the flash was read. Each unit was read once, "
                 "so that is not established, and neither is the cause. One 64-byte stretch "
                 "per image is the same in all three and is stored content. Crosses Repeated "
                 "Stretch says Yes when the bytes of a row's record or line overlap such a "
                 "stretch (40 bytes or more of one repeated two-byte value whose two bytes "
                 "differ). A line a stretch crosses can be cut, lost, or reported with the "
                 "repeated characters in its text: 2, 2 and 0 reported prompts in the three "
                 "images say Yes.",
        "paths": ('*/LargeOutputFiles/image.bin',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9 (LG), flash image | 0 rows, "
                             "no guidance prompt line in the image",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9 (LG), flash image | 362 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9 (LG), flash image | 0 "
                             "rows, no guidance prompt line in the image",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9 (LG), flash image | 0 rows, no "
                             "guidance prompt line in the image",
            "xtrmp_item033": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | 241 "
                             "rows",
            "xtrmp_item034": "2010 Cadillac CTS, OnStar Gen8 (Continental), flash image | 265 "
                             "rows",
            "xtrmp_item035": "2011 Cadillac CTS, OnStar Gen8 (Continental), flash image | 257 "
                             "rows",
        },
        "output_types": "standard",
        "artifact_icon": "corner-up-right",
    },
}

_RECORD = struct.Struct('>iiBBHHHBBBB')
_COORDINATE_UNITS = 6000000.0
_MIN_RUN = 5
# The two bytes of a big-endian year from 2005 to 2030, used to find candidate records.
_YEAR = re.compile(rb'\x07[\xd5-\xee]')
_LINE_TIME = rb'(\d{4})-(\d\d)-(\d\d):(\d\d)\.(\d\d)\.(\d\d)\.\d{3}:'
_DEST = re.compile(_LINE_TIME + rb'Dest lat (-?\d+) lon (-?\d+) \((-?[\d.]+),(-?[\d.]+)\)')
_PROMPT = re.compile(_LINE_TIME + rb'VIAMOTOSendHMIData audio \d+ [\d:]+ ([ -~]*?) street :?'
                     rb' ?([ -~]*?) distance ([ -~]*)')


def _images(context):
    """Matched image files, each read once."""
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'rb') as handle:
                yield file_found, handle.read()
        except OSError:
            continue


def _record(data, offset):
    """A position record at offset as (time, latitude, longitude, speed, heading), or None."""
    (latitude, longitude, month, day, year, speed, heading, hour, minute, second,
     _last) = _RECORD.unpack_from(data, offset)
    if not 2005 <= year <= 2030 or not latitude or not longitude:
        return None
    if abs(latitude) > 90 * _COORDINATE_UNITS or abs(longitude) > 180 * _COORDINATE_UNITS:
        return None
    try:
        stamp = datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
    return stamp, latitude, longitude, speed, heading


_STRETCH = re.compile(rb'(?s)(..)\1{19,}')


def _stretches(data):
    """(start, end) of each stretch of 40 bytes or more in which one two-byte value
    repeats, leaving out a value whose two bytes are equal (erased or zeroed space)."""
    return [(match.start(), match.end()) for match in _STRETCH.finditer(data)
            if match.group(1)[0] != match.group(1)[1]]


def _crosses(stretches, start, end):
    """'Yes' when the bytes from start to end overlap a stretch, else 'No'."""
    index = bisect.bisect_right(stretches, (start, len(stretches) and stretches[-1][1] + 1))
    for low, high in stretches[max(index - 1, 0):index + 1]:
        if low < end and start < high:
            return 'Yes'
    return 'No'


def _record_runs(data):
    """Offsets of position records that stand in runs, and the count left out as isolated.

    Candidates are located by the year field and tested as whole records. A run is a
    chain of valid records exactly 20 bytes apart; chains shorter than _MIN_RUN are not
    reported, because a lone valid-looking record can be chance.
    """
    valid = set()
    for match in _YEAR.finditer(data):
        offset = match.start() - 10
        if offset >= 0 and offset + _RECORD.size <= len(data) and _record(data, offset):
            valid.add(offset)
    kept = []
    isolated = 0
    for offset in sorted(valid):
        if offset - _RECORD.size in valid:
            continue
        length = 0
        position = offset
        while position in valid:
            length += 1
            position += _RECORD.size
        if length >= _MIN_RUN:
            kept.extend((offset + _RECORD.size * index, length) for index in range(length))
        else:
            isolated += length
    return kept, isolated


def _line_time(groups):
    try:
        return datetime(*(int(value) for value in groups[:6])).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


@artifact_processor
def gm_onstar_flash_gps_track(context):
    data_list = []
    source_paths = []
    for file_found, data in _images(context):
        kept, isolated = _record_runs(data)
        stretches = _stretches(data)
        rows = {}
        for offset, run_length in kept:
            stamp, latitude, longitude, speed, heading = _record(data, offset)
            key = (stamp.strftime('%Y-%m-%d %H:%M:%S'),
                   round(latitude / _COORDINATE_UNITS, 7),
                   round(longitude / _COORDINATE_UNITS, 7), round(speed * 0.0036, 1),
                   heading >> 7)
            if key in rows:
                rows[key][0] += 1
            else:
                rows[key] = [1, offset, run_length,
                             _crosses(stretches, offset, offset + _RECORD.size)]
        logfunc(f'GM OnStar flash image: {len(kept)} position records in runs, '
                f'{len(rows)} distinct, {isolated} isolated candidates left out, in '
                f'{os.path.basename(file_found)}')
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for key, (found, offset, run_length, crossed) in rows.items():
            data_list.append(key + (found, offset, run_length, crossed, relative))
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Speed (km/h)',
                    'Heading (degrees)', 'Times Found', 'Image Offset', 'Run Length',
                    'Crosses Repeated Stretch', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_onstar_flash_nav_destinations(context):
    data_list = []
    source_paths = []
    for file_found, data in _images(context):
        rows = {}
        stretches = _stretches(data)
        for match in _DEST.finditer(data):
            groups = match.groups()
            stamp = _line_time(groups)
            if not stamp:
                continue
            try:
                key = (stamp, float(groups[8]), float(groups[9]), int(groups[6]),
                       int(groups[7]))
            except ValueError:
                continue
            if key in rows:
                rows[key][0] += 1
            else:
                rows[key] = [1, match.start(),
                             _crosses(stretches, match.start(), match.end())]
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for key, (found, offset, crossed) in rows.items():
            data_list.append(key + (found, offset, crossed, relative))
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'Latitude (as stored)', 'Longitude (as stored)', 'Times Found',
                    'Image Offset', 'Crosses Repeated Stretch', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_onstar_flash_nav_guidance(context):
    data_list = []
    source_paths = []
    for file_found, data in _images(context):
        rows = {}
        stretches = _stretches(data)
        for match in _PROMPT.finditer(data):
            groups = match.groups()
            stamp = _line_time(groups)
            if not stamp:
                continue
            key = (stamp, groups[6].decode('latin-1'),
                   groups[7].decode('latin-1').replace('%20', ' '),
                   groups[8].decode('latin-1').strip())
            if key in rows:
                rows[key][0] += 1
            else:
                rows[key] = [1, match.start(),
                             _crosses(stretches, match.start(), match.end())]
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for key, (found, offset, crossed) in rows.items():
            data_list.append(key + (found, offset, crossed, relative))
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Prompt Time', 'datetime'), 'Maneuver', 'Street', 'Distance Text',
                    'Times Found', 'Image Offset', 'Crosses Repeated Stretch', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
