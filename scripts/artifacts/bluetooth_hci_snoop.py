"""Bluetooth HCI snoop captures (btsnoop files).

A btsnoop file is a 16-byte header ('btsnoop\\0', version, datalink type) followed by
records: original length, included length, flags, cumulative drops and a 64-bit time in
microseconds, each big-endian, then the packet. With datalink type 1002 (HCI UART) a
packet starts with one byte for its kind: 1 a command, 2 ACL data, 3 SCO data, 4 an
event.

    bt/btsnoop/btsnoop-filtered<n>.log    numbered files

The captures on the tested unit hold only HCI commands, in one or two sequences that each
open with HCI_Reset, and the controller's Command Complete answers. This module summarises
each capture: when its records start and end, how many packets of each kind it holds, and
the addresses, name and version numbers those answers state.

A capture is also looked for in a file of a volume's free space, at the start of a block.
"""

__artifacts_v2__ = {
    "bluetooth_hci_snoop_captures": {
        "name": "Bluetooth HCI Snoop - Captures",
        "description": "Bluetooth HCI snoop captures (btsnoop files), one row per capture, "
                       "with the first and last record time, the number of commands, events "
                       "and other packets, and the addresses, name and version numbers the "
                       "capture's Command Complete answers state.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Bluetooth HCI Snoop",
        "notes": "A btsnoop file opens with 'btsnoop', a version and a datalink type, then "
                 "holds records of an original length, an included length, flags, a drop "
                 "count, a 64-bit time and the packet. Files of version 1 with datalink type "
                 "1002 (HCI UART) are read, where the first byte of a packet says what it is: "
                 "1 a command, 4 an event, anything else counted as Other Packets. One row per "
                 "capture. The times are the first and the last record's, converted from the "
                 "format's count of microseconds since the start of year 0 with its stated "
                 "value for the start of 2000; the file states no time zone and none is "
                 "applied, so the report shows them as UTC. Last Record Time is the time of "
                 "the last record read, which is not always the latest. Read_BD_ADDR Answers "
                 "lists, in order, each distinct address in the answers to the Read_BD_ADDR "
                 "command (opcode 0x1009); a capture can hold more than one answer and they "
                 "can differ. Controller Name is the name in the Write_Local_Name command "
                 "(0x0C13) or the answer to Read_Local_Name (0x0C14), and the HCI version and "
                 "manufacturer are the numbers in the answer to Read_Local_Version_Information "
                 "(0x1001), as stored; the opcodes and layouts are those of the Bluetooth Core "
                 "Specification's HCI, checked against the BlueZ header that implements them. "
                 "An answer is used only when its status byte is zero. Reading stops at the "
                 "first record that is not whole, is malformed, or carries a time outside 2000 "
                 "to 2100, and Extent Read says how far it went; a capture whose first record "
                 "fails that gives no row. The free space of every volume a raw image input "
                 "offers (<image>.<volume>.unallocated.bin with its run map) is read too: a "
                 "capture is looked for at each 4,096 bytes of each free run, the block size "
                 "of the tested QNX6 volume, and only the records inside those 4,096 bytes are "
                 "read, because what follows a block in free space is not shown to be the same "
                 "file. A capture from free space is left out when a file, or an earlier "
                 "free-space capture, gave one with the same first record time, to the second, "
                 "and the same addresses; on the tested image none was. Each free-space row "
                 "carries its offset in the image. Tested on one Ford SYNC 4 unit, whose files "
                 "are bt/btsnoop/btsnoop-filtered<n>.log. The logical zip gave 4 rows, each a "
                 "whole file of 100 to 177 records, from 2024-03-27 to 2024-04-04; the raw "
                 "image gave 10, the same 4 and 6 from free space of 95 to 110 records each, "
                 "from 2023-12-06. Every capture held commands and events only, in near equal "
                 "numbers: each sequence opens with an HCI_Reset command and every event is a "
                 "Command Complete answer. None held an ACL or SCO packet or any other event. "
                 "All 10 stated one name and the same version numbers, and all 10 held the "
                 "same two differing Read_BD_ADDR answers in the same order, with vendor "
                 "commands between them; which of the two the controller used on the air is "
                 "not established here. In two captures from free space the record times step "
                 "back part way through, by about five hours in one, which later returns to "
                 "the later clock, and by about four hours in the other, at a second "
                 "HCI_Reset, so that one's last record time is earlier than its first. On the "
                 "4 files the last record time was within two seconds of the file's modified "
                 "time as the logical zip records it, a time that zip keeps to two seconds. A "
                 "row records that a btsnoop capture starting at that time was written. It "
                 "does not show that a phone was connected.",
        "paths": ('*/btsnoop/btsnoop*.log*', '*.unallocated.bin', '*.unallocated.tsv'),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 4 rows",
            "ford_syncg4": "Ford Sync 4, raw image | 10 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
}

import csv
import mmap
import os
import struct
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc

_MAGIC = b'btsnoop\x00'
_HEADER = struct.Struct('>8sII')
_RECORD = struct.Struct('>IIIIq')
_HCI_UART = 1002
# The format counts microseconds from midnight, January 1st, 0 AD. This is that count at
# midnight, January 1st, 2000.
_EPOCH_2000 = 0x00E03AB44A676000
_FREE_SPACE = '.unallocated.bin'
_RUN_MAP = '.unallocated.tsv'
_BLOCK = 4096
_MAX_PACKET = 65539
_COMMAND, _ACL, _SCO, _EVENT = 1, 2, 3, 4
_COMMAND_COMPLETE = 0x0E
_READ_LOCAL_VERSION = 0x1001
_READ_BD_ADDR = 0x1009
_WRITE_LOCAL_NAME = 0x0C13
_READ_LOCAL_NAME = 0x0C14


def _stamp(microseconds):
    """A record's time as 'YYYY-MM-DD HH:MM:SS', or '' when it is not a usable date."""
    try:
        moment = datetime(2000, 1, 1) + timedelta(microseconds=microseconds - _EPOCH_2000)
    except OverflowError:
        return ''
    if not 2000 <= moment.year <= 2100:
        return ''
    return moment.strftime('%Y-%m-%d %H:%M:%S')


def _name(raw):
    return raw.split(b'\x00')[0].decode('utf-8', 'replace')


def _summary(data):
    """What the records of one capture state, or None when data does not open with a
    version 1 HCI UART header. Reading stops at the first record that is not whole."""
    if len(data) < _HEADER.size:
        return None
    magic, version, datalink = _HEADER.unpack_from(data, 0)
    if magic != _MAGIC or version != 1 or datalink != _HCI_UART:
        return None
    found = {'first': '', 'last': '', 'records': 0, 'commands': 0, 'events': 0, 'other': 0,
             'addresses': [], 'name': '', 'hci_version': '', 'manufacturer': '', 'read': 0}
    offset = _HEADER.size
    while offset + _RECORD.size <= len(data):
        original, included, flags, _drops, moment = _RECORD.unpack_from(data, offset)
        end = offset + _RECORD.size + included
        if not 0 < included <= original <= _MAX_PACKET or flags > 3 or end > len(data):
            break
        stamp = _stamp(moment)
        if not stamp:
            break
        packet = data[offset + _RECORD.size:end]
        found['first'] = found['first'] or stamp
        found['last'] = stamp
        found['records'] += 1
        kind = packet[0]
        if kind == _COMMAND:
            found['commands'] += 1
            if len(packet) >= 4 and struct.unpack_from('<H', packet, 1)[0] == _WRITE_LOCAL_NAME:
                found['name'] = _name(packet[4:])
        elif kind == _EVENT:
            found['events'] += 1
            # event code, length, packets allowed, opcode, status, return values
            if len(packet) >= 7 and packet[1] == _COMMAND_COMPLETE and packet[6] == 0:
                opcode = struct.unpack_from('<H', packet, 4)[0]
                values = packet[7:]
                if opcode == _READ_BD_ADDR and len(values) >= 6:
                    address = ':'.join(f'{byte:02x}' for byte in values[5::-1])
                    # a capture can hold more than one answer, and they can differ
                    if address not in found['addresses']:
                        found['addresses'].append(address)
                elif opcode == _READ_LOCAL_NAME and values:
                    found['name'] = found['name'] or _name(values)
                elif opcode == _READ_LOCAL_VERSION and len(values) >= 8:
                    found['hci_version'] = values[0]
                    found['manufacturer'] = struct.unpack_from('<H', values, 4)[0]
        else:
            found['other'] += 1
        offset = end
    found['read'] = offset
    if not found['records']:
        return None
    return found


def _free_runs(path, size):
    """(offset in the file, offset in the image, length) for each run of a free space
    file, from the run map beside it. Without a usable map the file is one run and no
    image offset is known."""
    runs = []
    try:
        with open(path[:-len(_FREE_SPACE)] + _RUN_MAP, encoding='utf-8', newline='') as handle:
            for row in list(csv.reader(handle, delimiter='\t'))[1:]:
                runs.append((int(row[0]), int(row[1]), int(row[2])))
    except (OSError, ValueError, IndexError):
        runs = []
    if not runs or sum(length for _start, _image, length in runs) != size:
        logfunc(f'Bluetooth HCI snoop: no usable run map beside {os.path.basename(path)}')
        return [(0, None, size)]
    return runs


def _free_space_captures(path):
    """(summary, offset in the image or None) for each capture that starts a 4,096-byte
    step of a free run. Only the records inside those first 4,096 bytes are read: what
    follows a block in free space is not shown to be the same file."""
    try:
        size = os.path.getsize(path)
        if not size:
            return
        handle = open(path, 'rb')  # pylint: disable=consider-using-with
    except OSError:
        return
    try:
        mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
    except (OSError, ValueError):
        handle.close()
        return
    try:
        for start, image, length in _free_runs(path, size):
            position = mapped.find(_MAGIC, start, start + length)
            while position != -1:
                if (position - start) % _BLOCK == 0:
                    found = _summary(mapped[position:min(start + length, position + _BLOCK)])
                    if found is not None:
                        yield found, None if image is None else image + position - start
                position = mapped.find(_MAGIC, position + 1, start + length)
    finally:
        mapped.close()
        handle.close()


def _row(found, extent, store, name, where):
    return (found['first'], found['last'], found['records'], found['commands'],
            found['events'], found['other'], ', '.join(found['addresses']), found['name'],
            found['hci_version'], found['manufacturer'], extent, store, name, where)


@artifact_processor
def bluetooth_hci_snoop_captures(context):
    data_list = []
    source_paths = []
    seen = set()
    files = sorted(str(f) for f in set(context.get_files_found()) if not os.path.isdir(str(f)))
    for file_found in files:
        if file_found.endswith((_FREE_SPACE, _RUN_MAP)):
            continue
        try:
            with open(file_found, 'rb') as handle:
                data = handle.read()
        except OSError:
            continue
        found = _summary(data)
        if found is None:
            continue
        extent = 'Whole file' if found['read'] == len(data) else \
            f"First {found['read']:,} of {len(data):,} bytes"
        seen.add((found['first'], tuple(found['addresses'])))
        source_paths.append(file_found)
        data_list.append(_row(found, extent, 'File', os.path.basename(file_found), ''))
    # Free space: a capture already given, by first record time and addresses, is left out.
    for file_found in files:
        if not file_found.endswith(_FREE_SPACE):
            continue
        used = False
        for found, where in _free_space_captures(file_found):
            key = (found['first'], tuple(found['addresses']))
            if key in seen:
                continue
            seen.add(key)
            used = True
            data_list.append(_row(found, f"First {found['read']:,} bytes of a free block",
                                  'Free space', os.path.basename(file_found),
                                  '' if where is None else where))
        if used:
            source_paths.append(file_found)
    data_list.sort(key=lambda row: row[0])

    data_headers = (('First Record Time', 'datetime'), ('Last Record Time', 'datetime'),
                    'Records Read', 'Commands', 'Events', 'Other Packets',
                    'Read_BD_ADDR Answers', 'Controller Name', 'HCI Version (as stored)',
                    'Manufacturer (as stored)', 'Extent Read', 'Store', 'File Name',
                    'Offset In Image')
    return data_headers, data_list, '\n'.join(source_paths)
