"""Ford SYNC on Windows CE, generation 1: the speech recogniser's person name cache.

The module keeps, beside its other Windows files, a cache its speech recogniser holds
for person names, each name with a string the recogniser stored for it:

    Windows/<language>_ddg2p_person_name_cache.cac

The unit's own speech configuration, Application Data/speng.rgs, registers the file. Under
the recogniser token it names 'Nuance VoCon3200 Recognizer American English', key ddg2p,
subkey C carries InputType 'PERSON_NAME', CacheFile 'enu_ddg2p_person_name_cache.cac' and
CacheCapacity 2000. The same block is on all five units that have the file.

The configuration does not describe the records. The layout below was worked out from
five units and every length in it is checked against the file before a record is read:

    u32  file size
    u16  capacity (2000 in every tested file, the configured CacheCapacity)
    u16  entry count
    per entry:
        u16  record length
        6 bytes read as u16, u8, u8 (1, 1, 1 on every tested entry) and a
        u16  G2P string length, the string's two closing NULs included
        the G2P string, 8-bit, padded to an even length
        u16  entry number, each value from 0 to count - 1 once in a file
        u16  name length in bytes
        the name, UTF-16LE, NUL terminated
    then one u16 for each entry and one more, not read

"G2P string" is this module's label, after the key (ddg2p) and the G2PCacheFile value in
the configuration; no vendor description of the string was read.

Two sibling files hold the same record layout on the five tested units and are left out:
<language>_ddg2p_mp3_cache.cac, which the configuration registers with InputType
'MPTHREE', and <language>_g2pcache.cac, its G2PCacheFile.
"""

import os
import struct

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "ford_sync_wince_voice_name_cache": {
        "name": "Ford SYNC WinCE - Voice Name Cache",
        "description": "Names in the cache the module's speech recogniser keeps for person "
                       "names, each with the string stored with it, its entry number and its "
                       "position in the file.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/<language>_ddg2p_person_name_cache.cac, which the tested units "
                 "name enu_ddg2p_person_name_cache.cac. The unit's speech configuration, "
                 "Application Data/speng.rgs, registers that file under the recogniser token "
                 "it names 'Nuance VoCon3200 Recognizer American English', key ddg2p, with "
                 "InputType 'PERSON_NAME' and CacheCapacity 2000. The record layout is not "
                 "described there; it was worked out from the files and is given in the "
                 "module. Every record is read by the lengths it states, and a file whose "
                 "stated size is not its own size, or a record whose lengths do not fit, is "
                 "logged and reading stops there. Tested on eight SYNC Gen1 units and one "
                 "SYNC Gen2 unit from their acquisition folders. Five Gen1 units have the "
                 "file (Ford Escape 2010, 2011 and 2012, Ford Edge 2013) and gave 2,760 rows, "
                 "each file read to its stated entry count, 159 to 988 entries a file. The "
                 "other three Gen1 units and the Gen2 unit have no such file. Two of those, "
                 "the Gen1 version 3 units, configure a cache named "
                 "<language>_clc_person_name_cache.cac instead; it was not present on either "
                 "and this artifact does not match that name. Name is the entry's text, "
                 "stored as UTF-16. Name was never empty. G2P String is the 8-bit string "
                 "stored before the name, shown without its closing NULs; G2P is this "
                 "artifact's label for it, after the configuration's key names. On every "
                 "tested row it starts and ends with '#'. What its symbols stand for was not "
                 "looked up. Entry Number is a 16-bit value stored in each entry: in every "
                 "tested file each number from 0 to one less than the entry count appears "
                 "once, and the entries are not stored in that order. What the number orders "
                 "is not established. Position In File is the entry's place in the file, "
                 "counted from 1. An entry carries no phone number, no handset address and "
                 "no date. Nothing read from the file names a handset; the values after the "
                 "last entry are not read. Compared with the Phonebook and Persistent "
                 "Phonebook Names artifacts of the same units by text, ignoring case and "
                 "leading or trailing spaces: 1,769 of the 2,760 rows (966, 73, 1, 532 and "
                 "197 on the five units) are text those artifacts do not list for that unit. "
                 "On the 2011 Ford Escape with 609 rows, the 77 rows whose text those "
                 "artifacts also list hold entry numbers between 486 and 608. Why a name is "
                 "in the cache and not in a phonebook file is not established. Not every "
                 "entry need be a contact: the comparison is by text only. A row records "
                 "that the cache held this text. It does not establish that a number was "
                 "dialled or who used the handset. Two sibling files that hold the same "
                 "record layout on the five tested units are not reported: "
                 "<language>_ddg2p_mp3_cache.cac, which the configuration registers with "
                 "InputType 'MPTHREE' and which holds media text, and "
                 "<language>_g2pcache.cac, which it names as the recogniser's G2PCacheFile "
                 "and whose text was not characterised. Any language prefix is matched; only "
                 "enu was available to test.",
        "paths": ('*/Windows/*_ddg2p_person_name_cache.cac',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 988 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 626 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 159 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 609 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 0 rows, no "
                             "name cache file",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 0 rows, no "
                             "name cache file",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 0 rows, no "
                             "name cache file",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 0 rows, no "
                             "name cache file",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 378 rows",
        },
        "output_types": "standard",
        "artifact_icon": "mic",
    },
}

_HEADER = struct.Struct('<IHH')
_RECORD = struct.Struct('<HHBBH')
_BEFORE_NAME = struct.Struct('<HH')


def _entries(data):
    """(entries, declared count, problem) for one cache file.

    An entry is (name, G2P string, entry number, position). Reading stops at the
    first record whose lengths do not fit, and the entries read before it are kept.
    problem is '' when the whole declared count was read.
    """
    if len(data) < _HEADER.size:
        return [], 0, 'shorter than its header'
    size, _capacity, count = _HEADER.unpack_from(data, 0)
    if size != len(data):
        return [], count, f'states a size of {size} bytes and is {len(data)}'
    entries = []
    offset = _HEADER.size
    for position in range(1, count + 1):
        if offset + _RECORD.size > len(data):
            return entries, count, f'ends before entry {position}'
        record_length, _a, _b, _c, spoken_length = _RECORD.unpack_from(data, offset)
        spoken_start = offset + _RECORD.size
        before_name = spoken_start + spoken_length + spoken_length % 2
        name_start = before_name + _BEFORE_NAME.size
        if offset + record_length > len(data) or name_start > offset + record_length:
            return entries, count, f'entry {position} has lengths that do not fit the file'
        number, name_length = _BEFORE_NAME.unpack_from(data, before_name)
        if name_start + name_length > offset + record_length:
            return entries, count, f'entry {position} has a name longer than its record'
        raw = data[name_start:name_start + name_length]
        raw = raw[:len(raw) - len(raw) % 2]
        name = raw.decode('utf-16-le', 'replace').split('\x00', 1)[0]
        spoken = data[spoken_start:spoken_start + spoken_length].rstrip(b'\x00')
        entries.append((name, spoken.decode('latin-1'), number, position))
        offset += record_length
    return entries, count, ''


@artifact_processor
def ford_sync_wince_voice_name_cache(context):
    data_list = []
    source_paths = []
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        try:
            with open(file_found, 'rb') as handle:
                data = handle.read()
        except OSError:
            logfunc(f'Ford SYNC WinCE voice name cache: {base} could not be opened, not read')
            continue
        source_paths.append(file_found)
        entries, count, problem = _entries(data)
        if problem:
            logfunc(f'Ford SYNC WinCE voice name cache: {base} {problem}; read '
                    f'{len(entries)} of {count} entries')
        data_list.extend(entries)

    data_headers = ('Name', 'G2P String (as stored)', 'Entry Number (as stored)',
                    'Position In File')
    return data_headers, data_list, '\n'.join(source_paths)
