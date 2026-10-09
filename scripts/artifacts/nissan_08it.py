"""Nissan 08IT infotainment head unit (hard-disk navigation unit), generations 3000 and 8000.

Named for the module: the vehicle model behind each tested unit is not recorded, so the
module name is the only identity these files share. The telephone data sits in fixed-size
binary records under a TEL folder, keyed by the handset's Bluetooth address in the file
name:

    TEL/CALLLOGS/f_incoming<address>.txt, f_outgoing..., f_miss...   call lists
    TEL/HF_MEMORY/f_hf_memory<address>.txt                           the handset phonebook
    TEL/INFO/f_info.txt or f_phonebookinfo.txt                       the device table

The two generations use different record layouts for the same files. Each reader picks
the layout from the file's own size and record markers and gives the file up, with a log
line, when neither fits.
"""

import os
import re
import struct
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "nissan_08it_call_logs": {
        "name": "Nissan 08IT - Call Logs",
        "description": "Entries of the incoming, outgoing and missed call files the head unit "
                       "keeps for each handset, with the call clock reading, the phone number "
                       "and, on generation 8000, the name stored in each entry.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/CALLLOGS/f_incoming<address>.txt, f_outgoing<address>.txt and "
                 "f_miss<address>.txt. Despite the extension they are binary files of "
                 "fixed-size records after a four-byte count. Tested on two units, one of "
                 "generation 3000 and one of generation 8000, read from the file sets "
                 "extracted from each unit's hard disk; the vehicle model behind each is not "
                 "recorded. Call List is taken from the file name. Handset Address is the "
                 "twelve hex digits in the file name, shown with colons. Generation 3000 "
                 "stores 102-byte records with an ASCII number and a big-endian date; "
                 "generation 8000 stores 192-byte records with a UTF-16 name, an ASCII number "
                 "and a little-endian date, and marks each used record with fixed bytes. The "
                 "layout is chosen from the file size and those marks, Record Layout says "
                 "which was used, and a file that fits neither is logged and not read. Only "
                 "the number of records the count states is read. The generation 3000 unit "
                 "held one incoming file of 20 entries, and for the two entries compared an "
                 "independent parse of the same file gave the same times and the same list. "
                 "The generation 8000 unit held 15 files for five handsets, with 32 entries in "
                 "four of them. The record holds no time zone, so the time is the unit's clock "
                 "reading, written out as if it were UTC with no offset applied. Record Value "
                 "is the byte after the date on generation 3000 and the four-byte value before "
                 "it on generation 8000; nothing available here documents either. Name is "
                 "empty on generation 3000 because its record has no name field. An entry "
                 "records that the unit held this call list entry for the handset. It does not "
                 "establish who used the handset.",
        "paths": ('*/TEL/CALLLOGS/f_*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 20 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 32 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "nissan_08it_phone_memory": {
        "name": "Nissan 08IT - Handset Phonebook",
        "description": "Entries of the phonebook file the head unit keeps for each handset, "
                       "with the name and the phone numbers stored in each entry.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/HF_MEMORY/f_hf_memory<address>.txt on generation 8000, a binary "
                 "file of 384-byte records after a four-byte count: an index, a UTF-16 name "
                 "and five number slots, each an ASCII number with a four-byte value. Tested "
                 "on two units, one of generation 3000 and one of generation 8000, read from "
                 "the file sets extracted from each unit's hard disk; the vehicle model behind "
                 "each is not recorded. The generation 8000 unit held five such files, one per "
                 "handset; one held 270 entries and four held none. The generation 3000 unit "
                 "had no HF_MEMORY folder in its extracted set. A file whose size or record "
                 "marks do not fit is logged and not read. Number Values are the four-byte "
                 "value of each number slot, in the same order as Phone Numbers; 2, 3 and 9 "
                 "occur and nothing available here documents them. Handset Address is the "
                 "twelve hex digits in the file name, shown with colons. An entry records that "
                 "the unit held the contact for that handset. It does not establish that any "
                 "number was dialled.",
        "paths": ('*/TEL/HF_MEMORY/f_hf_memory*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "HF_MEMORY folder in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 270 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "nissan_08it_devices": {
        "name": "Nissan 08IT - Bluetooth Device Table",
        "description": "Slots of the head unit's Bluetooth device table, with the handset "
                       "address stored in each occupied slot and, on generation 8000, the "
                       "device name.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/INFO/f_info.txt on generation 8000 (164-byte slots holding an "
                 "address and a name) and TEL/INFO/f_phonebookinfo.txt on generation 3000 "
                 "(104-byte slots holding an address). Tested on two units, one of generation "
                 "3000 and one of generation 8000, read from the file sets extracted from each "
                 "unit's hard disk; the vehicle model behind each is not recorded. Each held "
                 "five slots, with five occupied on generation 8000 and four on generation "
                 "3000. The address is stored as twelve ASCII hex digits and is shown with "
                 "colons when all twelve are present. On the generation 3000 unit three of the "
                 "four addresses had a NUL byte in place of their first digit; those are shown "
                 "with a question mark in that position and without colons, and what the NUL "
                 "means is not established here. The rest of each slot is not decoded. A slot "
                 "records that the unit held an entry for the device. It does not establish "
                 "who carried it. Not read from the same units: the compressed location debug "
                 "logs under USER/DEBUG/LOC, whose 2,048-byte blocks have no layout "
                 "established here, and the voice tag, learning and backup files.",
        "paths": ('*/TEL/INFO/f_info.txt*', '*/TEL/INFO/f_phonebookinfo.txt*'),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 4 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 5 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
}

# The call list files name their own list.
_CALL_FILES = (('f_incoming', 'Incoming'), ('f_outgoing', 'Outgoing'), ('f_miss', 'Missed'))
_TEXT_MARK = bytes.fromhex('0b010200')
_NUMBER_MARK = bytes.fromhex('0300ff80')
_HEX12 = re.compile(r'[0-9A-Fa-f]{12}')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return b''


def _address(text):
    if _HEX12.fullmatch(text or ''):
        return ':'.join(text[i:i + 2] for i in range(0, 12, 2)).lower()
    return text or ''


def _address_from_name(path, prefix):
    match = _HEX12.match(os.path.basename(path)[len(prefix):])
    return _address(match.group(0)) if match else ''


def _ascii(raw):
    return raw.split(b'\x00', 1)[0].decode('latin-1')


def _wide_be(raw):
    """A NUL-terminated UTF-16 big-endian string from a fixed field."""
    raw = raw[:len(raw) - len(raw) % 2]
    for index in range(0, len(raw), 2):
        if raw[index:index + 2] == b'\x00\x00':
            raw = raw[:index]
            break
    return raw.decode('utf-16-be', 'replace')


def _stamp(year, month, day, hour, minute, second):
    try:
        return datetime(year, month, day, hour, minute, second).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


# ---------------------------------------------------------------------------
# Call logs
# ---------------------------------------------------------------------------

def _calls_3000(data):
    """Generation 3000: a big-endian count, then 102-byte records of an ASCII number
    and a seven-field big-endian date."""
    body = len(data) - 4
    if body <= 0 or body % 102:
        return None
    count = struct.unpack('>I', data[:4])[0]
    if count > body // 102:
        return None
    rows = []
    for index in range(count):
        record = data[4 + 102 * index:4 + 102 * (index + 1)]
        year, month, day, hour, minute, second, last = struct.unpack('>HBBBBBB',
                                                                     record[94:102])
        rows.append((_stamp(year, month, day, hour, minute, second), '',
                     _ascii(record[:94]), last, index + 1))
    return rows


def _calls_8000(data):
    """Generation 8000: a little-endian count, then 192-byte records holding a UTF-16
    name, an ASCII number, a four-byte value and a little-endian date. Each used record
    carries fixed marker bytes, which is what tells this layout from the other."""
    body = len(data) - 4
    if body <= 0 or body % 192:
        return None
    count = struct.unpack('<I', data[:4])[0]
    if count > body // 192:
        return None
    rows = []
    for index in range(count):
        record = data[4 + 192 * index:4 + 192 * (index + 1)]
        if record[0x40:0x44] != _TEXT_MARK or record[0xb0:0xb4] != _NUMBER_MARK:
            return None
        year, month, day, hour, minute, second, _last = struct.unpack('<HBBBBBB',
                                                                      record[0xb8:0xc0])
        rows.append((_stamp(year, month, day, hour, minute, second),
                     _wide_be(record[0:0x40]), _ascii(record[0x88:0xb0]),
                     struct.unpack('<I', record[0xb4:0xb8])[0], index + 1))
    return rows


@artifact_processor
def nissan_08it_call_logs(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        kind = next(((prefix, label) for prefix, label in _CALL_FILES
                     if base.startswith(prefix)), None)
        if kind is None:
            continue
        data = _read(file_found)
        rows = _calls_8000(data)
        layout = '8000'
        if rows is None:
            rows = _calls_3000(data)
            layout = '3000'
        if rows is None:
            logfunc(f'Nissan 08IT call logs: {base} ({len(data)} bytes) fits neither record '
                    'layout, not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, kind[0])
        for stamp, name, number, value, position in rows:
            data_list.append((stamp, kind[1], name, number, value, position, address,
                              layout, context.get_relative_path(file_found)))

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Name', 'Phone Number',
                    'Record Value (as stored)', 'Position In File', 'Handset Address',
                    'Record Layout', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Handset phonebook
# ---------------------------------------------------------------------------

def _phone_memory(data):
    """Generation 8000 phonebook: a little-endian count, then 384-byte records holding
    an index, a UTF-16 name and five number slots, each slot an ASCII number, a marker
    and a four-byte value."""
    body = len(data) - 4
    if body <= 0 or body % 384:
        return None
    count = struct.unpack('<I', data[:4])[0]
    if count > body // 384:
        return None
    rows = []
    for position in range(count):
        record = data[4 + 384 * position:4 + 384 * (position + 1)]
        if record[0x48:0x4c] != _TEXT_MARK or record[0xb8:0xbc] != _NUMBER_MARK:
            return None
        numbers = []
        values = []
        for slot in range(5):
            start = 0x90 + 48 * slot
            number = _ascii(record[start:start + 40])
            if number:
                numbers.append(number)
                values.append(str(struct.unpack('<I', record[start + 44:start + 48])[0]))
        rows.append((_wide_be(record[0x08:0x48]), '; '.join(numbers), '; '.join(values),
                     struct.unpack('<I', record[:4])[0], position + 1))
    return rows


@artifact_processor
def nissan_08it_phone_memory(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if not base.startswith('f_hf_memory'):
            continue
        data = _read(file_found)
        rows = _phone_memory(data)
        if rows is None:
            logfunc(f'Nissan 08IT phonebook: {base} ({len(data)} bytes) does not fit the '
                    'record layout, not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, 'f_hf_memory')
        for name, numbers, values, index, position in rows:
            data_list.append((address, name, numbers, values, index, position,
                              context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'Name', 'Phone Numbers', 'Number Values (as stored)',
                    'Entry Index', 'Position In File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Device table
# ---------------------------------------------------------------------------

@artifact_processor
def nissan_08it_devices(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        data = _read(file_found)
        if base.startswith('f_info.txt'):
            size, layout = 164, '8000'
        elif base.startswith('f_phonebookinfo.txt'):
            size, layout = 104, '3000'
        else:
            continue
        if not data or len(data) % size:
            logfunc(f'Nissan 08IT devices: {base} ({len(data)} bytes) is not a whole number '
                    f'of {size}-byte slots, not read')
            continue
        found = False
        for slot in range(len(data) // size):
            record = data[slot * size:(slot + 1) * size]
            if not any(record[:16]):
                continue
            # A slot whose first address character is NUL keeps the other eleven.
            address = record[:12].replace(b'\x00', b'?').decode('latin-1')
            name = _ascii(record[0x40:0x60]) if layout == '8000' else ''
            found = True
            data_list.append((slot + 1, _address(address), name, layout,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = ('Slot', 'Handset Address (as stored)', 'Device Name', 'Record Layout',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
