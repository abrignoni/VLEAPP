"""Ford SYNC on Windows CE: the module's registry hive files.

The module keeps its registry in two hive files:

    Documents and Settings/system.hv
    Documents and Settings/<profile>/user.hv

No published description of the file layout was found, so the layout below was worked
out from the files themselves and is checked on every cell as it is read:

    0x0008  the four bytes 'EKIM'
    0x1000  a list of 32-bit offsets, one per identifier table, relative to 0x5000
    table   a 12-byte cell header, then 1,024 entries of 32 bits. An entry with its low
            bit set gives a cell's offset, relative to 0x5000, in bits 2 to 27.
    cell    32 bits holding the payload size (low 28 bits) and the cell kind (top 4
            bits), 32 bits not read here, then the cell's own identifier.
    key     kind 0xC: next sibling, first child and first value identifiers, a one-byte
            name length in characters, then the name as UTF-16LE
    value   kind 0xD: next value identifier, 16-bit data type, 16-bit data length, a
            one-byte name length, a one-byte flag, the name, then the data

A cell is used only when the identifier it carries is the one its table entry was found
under. Identifiers with bits set in their top four do not resolve inside the file and are
not followed.
"""

import re
import struct

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "ford_sync_wince_registry_bt_devices": {
        "name": "Ford SYNC WinCE - Registry Bluetooth Devices",
        "description": "Bluetooth devices named in the module's registry hive, one row per "
                       "device address, with the device name, pair time, phone make and model "
                       "strings and connection settings stored under it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Documents and Settings/system.hv and Documents and "
                 "Settings/<profile>/user.hv, the module's registry hive files (marker EKIM). "
                 "No published description of the layout was found; it was worked out from the "
                 "files and is described in the module. A cell is read only when the "
                 "identifier it carries is the one its table entry was found under. Tested on "
                 "ten units read from their extracted file sets: eight SYNC Gen1 (Ford Escape "
                 "2010 to 2014, Edge 2013, Fusion 2019) and two SYNC Gen2 (2014 Ford Edge SEL, "
                 "2011 Ford Explorer XLT). On the eight Gen1 units every cell passed that "
                 "check. On the two Gen2 units 1,214 cells did not, 1,162 of them because the "
                 "extracted file holds zeros where the table points; those cells are counted "
                 "in the log and not read, so the Gen2 output is partial. A device is any key "
                 "whose name is twelve hexadecimal characters, or a value named key plus "
                 "twelve; rows are grouped on those characters, which are reported as the key "
                 "holds them and are taken to be the device's Bluetooth address. Nine units "
                 "gave 23 rows and one Gen2 unit gave none. Each of the 23 addresses also "
                 "appears in a file or folder name elsewhere in the same extraction, and on "
                 "one unit an independent parse lists the same address. Device Name, the "
                 "manufacturer, model, serial number and version strings and the numeric "
                 "settings are the values of those names as stored; what the module uses each "
                 "number for is not established here. Link Key Value Present says only that a "
                 "value named for the address exists under the security key; its 132 bytes are "
                 "in the Registry Values artifact. Pair Time is a 16-byte calendar structure "
                 "with no zone, written from the module's own clock: 22 of the 23 rows read in "
                 "2003, which is consistent with a clock that was not set, so treat the time "
                 "as stored and not as a date. Key Paths lists the keys the address was found "
                 "under. A row records that the hive names the device. It does not establish "
                 "when it was last connected.",
        "paths": ('*/Documents and Settings/*.hv',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 1 row",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, extracted file set | 1 row",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 2 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 4 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 4 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 2 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 1 row",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no device key among the cells that could be read",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 3 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 5 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "ford_sync_wince_registry_values": {
        "name": "Ford SYNC WinCE - Registry Values",
        "description": "Values read from the module's registry hive files, each with its key "
                       "path, name, stored type number and data.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Documents and Settings/system.hv and Documents and "
                 "Settings/<profile>/user.hv, the module's registry hive files (marker EKIM). "
                 "No published description of the layout was found; it was worked out from the "
                 "files and is described in the module. A cell is read only when the "
                 "identifier it carries is the one its table entry was found under. Tested on "
                 "ten units read from their extracted file sets: eight SYNC Gen1 (Ford Escape "
                 "2010 to 2014, Edge 2013, Fusion 2019) and two SYNC Gen2 (2014 Ford Edge SEL, "
                 "2011 Ford Explorer XLT). On the eight Gen1 units every cell passed that "
                 "check. On the two Gen2 units 1,214 cells did not, 1,162 of them because the "
                 "extracted file holds zeros where the table points; those cells are counted "
                 "in the log and not read, so the Gen2 output is partial. The ten units gave "
                 "6,785 rows, from 127 to 2,930 a unit. It lists the values the reader "
                 "reached, and most of them are system configuration; it is here so a value "
                 "can be looked up by key path. Keys that varied between units include the "
                 "Bluetooth pairing and security keys, the phone application's device keys, "
                 "attached USB device names, vehicle health report settings and, on the 2019 "
                 "Fusion, a policy table of 1,898 values. Key Path starts at the highest key "
                 "the file holds. Sibling, child and value references with bits set in their "
                 "top four do not resolve inside the file and are not followed, so keys "
                 "reachable only through them are not listed; where they lead is not "
                 "established. Data is shown by its shape: type 4 with four bytes as an "
                 "unsigned number, types 1 and 2 as text, type 7 as a text list, anything else "
                 "as hexadecimal with the first 64 bytes shown and the full length in Data "
                 "Length. Data Read As says which was used. 19 type 4 values were not four "
                 "bytes and are shown as bytes. The type numbers are given as stored and not "
                 "named.",
        "paths": ('*/Documents and Settings/*.hv',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 347 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, extracted file set | 403 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 385 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 477 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 574 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 2930 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 489 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 127 rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 512 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 541 rows",
        },
        "output_types": "standard",
        "artifact_icon": "database",
    },
}

_BASE = 0x5000
_TABLE_LIST = 0x1000
_TABLE_HEADER = 0x20001004
_TABLE_ENTRIES = 1024
_KIND_KEY = 0xC
_KIND_VALUE = 0xD
_HEX_BYTES_SHOWN = 64
_ADDRESS_KEY = re.compile(r'^[0-9a-fA-F]{12}$')
_ADDRESS_VALUE = re.compile(r'^key([0-9a-fA-F]{12})$')


def _hive_files(context):
    return sorted(str(found) for found in context.get_files_found()
                  if str(found).lower().endswith('.hv'))


def _load(data):
    """Return (keys, values, skipped) for one hive, or None when it is not one."""
    if len(data) < _TABLE_LIST + 4 * _TABLE_ENTRIES or data[8:12] != b'EKIM':
        return None
    offsets = {}
    for number, relative in enumerate(struct.unpack_from('<%dI' % _TABLE_ENTRIES, data, _TABLE_LIST)):
        table = relative + _BASE
        if number and not relative:
            break
        if table + 12 + 4 * _TABLE_ENTRIES > len(data):
            break
        if struct.unpack_from('<I', data, table)[0] != _TABLE_HEADER:
            break
        entries = struct.unpack_from('<%dI' % _TABLE_ENTRIES, data, table + 12)
        for index, entry in enumerate(entries):
            if entry & 1:
                offsets[number * _TABLE_ENTRIES + index] = (entry & 0x0FFFFFFC) + _BASE
    keys = {}
    values = {}
    skipped = 0
    for identifier, offset in offsets.items():
        if offset + 28 > len(data):
            skipped += 1
            continue
        header, _, own = struct.unpack_from('<III', data, offset)
        kind = header >> 28
        size = header & 0x0FFFFFFF
        payload = offset + 12
        if own != identifier or payload + size > len(data):
            skipped += 1
            continue
        if kind == _KIND_KEY:
            sibling, child, value, name_length = struct.unpack_from('<IIIB', data, payload)
            if 16 + 2 * name_length > size:
                skipped += 1
                continue
            name = data[payload + 16:payload + 16 + 2 * name_length].decode('utf-16le', 'replace')
            keys[identifier] = (sibling, child, value, name)
        elif kind == _KIND_VALUE:
            following, data_type, data_length, name_length = struct.unpack_from('<IHHB', data, payload)
            start = payload + 10 + 2 * name_length
            if 10 + 2 * name_length + data_length > size:
                skipped += 1
                continue
            name = data[payload + 10:start].decode('utf-16le', 'replace')
            values[identifier] = (following, data_type, name, data[start:start + data_length])
    return keys, values, skipped


def _inside(reference):
    return reference and not reference >> 28


def _walk(keys, values):
    """Yield (key path parts, value name, data type, data) for every value a key leads to."""
    referenced = set()
    for sibling, child, _, _ in keys.values():
        if _inside(sibling):
            referenced.add(sibling)
        if _inside(child):
            referenced.add(child)
    seen_keys = set()
    seen_values = set()
    rows = []
    pending = [(identifier, ()) for identifier in sorted(keys, reverse=True)
               if identifier not in referenced]
    while pending:
        identifier, parent = pending.pop()
        if identifier not in keys or identifier in seen_keys:
            continue
        seen_keys.add(identifier)
        sibling, child, value, name = keys[identifier]
        parts = parent + (name,)
        while _inside(value) and value in values and value not in seen_values:
            seen_values.add(value)
            following, data_type, value_name, data = values[value]
            rows.append((parts, value_name, data_type, data))
            value = following
        if _inside(sibling):
            pending.append((sibling, parent))
        if _inside(child):
            pending.append((child, parts))
    return rows


def _text(data):
    return data.decode('utf-16le', 'replace').split('\x00')[0]


def _render(data_type, data):
    """Return (shown, how it was read). The stored type number decides nothing on its own."""
    if data_type == 4 and len(data) == 4:
        return str(struct.unpack('<I', data)[0]), 'number, 32 bits'
    if data_type in (1, 2) and len(data) % 2 == 0:
        return _text(data), 'text'
    if data_type == 7 and len(data) % 2 == 0:
        parts = [part for part in data.decode('utf-16le', 'replace').split('\x00') if part]
        return ' | '.join(parts), 'text list'
    shown = data[:_HEX_BYTES_SHOWN].hex()
    if len(data) > _HEX_BYTES_SHOWN:
        return shown + '...', 'bytes, first %d shown' % _HEX_BYTES_SHOWN
    return shown, 'bytes'


def _system_time(data):
    if len(data) != 16:
        return ''
    year, month, _, day, hour, minute, second, _ = struct.unpack('<8H', data)
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60 and second < 60):
        return ''
    return '%04d-%02d-%02d %02d:%02d:%02d' % (year, month, day, hour, minute, second)


def _hives(context):
    for path in _hive_files(context):
        with open(path, 'rb') as handle:
            data = handle.read()
        loaded = _load(data)
        if loaded is None:
            logfunc('Ford SYNC WinCE registry: %s is not a hive this reader knows, not read'
                    % context.get_relative_path(path))
            continue
        keys, values, skipped = loaded
        if skipped:
            logfunc('Ford SYNC WinCE registry: %d cells of %s did not hold what their table '
                    'entry named and were not read' % (skipped, context.get_relative_path(path)))
        yield path, _walk(keys, values)


@artifact_processor
def ford_sync_wince_registry_values(context):
    data_headers = ('Key Path', 'Value Name', 'Data', 'Data Read As', 'Type (as stored)',
                    'Data Length', 'Source File')
    data_list = []
    source_paths = []
    for path, rows in _hives(context):
        relative = context.get_relative_path(path)
        if rows:
            source_paths.append(path)
        for parts, name, data_type, data in rows:
            shown, how = _render(data_type, data)
            data_list.append(('\\'.join(parts), name, shown, how, data_type, len(data), relative))
    return data_headers, data_list, '\n'.join(source_paths)


_DEVICE_FIELDS = (
    # (key name the value sits in below the address key, value name, column index)
    ('', 'DeviceName', 2),
    ('Attributes', 'Manuf', 3),
    ('Attributes', 'Model', 4),
    ('Attributes', 'SerialNumber', 5),
    ('Attributes', 'Version', 6),
    ('', 'ProfileCount', 7),
    ('', 'Primary', 9),
    ('', 'HFPConnections', 10),
    ('', 'BTAVConnections', 11),
    ('', 'PBDownload', 12),
)


@artifact_processor
def ford_sync_wince_registry_bt_devices(context):
    data_headers = ('Pair Time (as stored)', 'Address In Key Name', 'Device Name',
                    'Manufacturer (as stored)', 'Model (as stored)',
                    'Serial Number (as stored)', 'Version (as stored)',
                    'Profile Count', 'Link Key Value Present', 'Primary (as stored)',
                    'HFP Connections (as stored)', 'BTAV Connections (as stored)',
                    'Phonebook Download (as stored)', 'Key Paths', 'Source File')
    data_list = []
    source_paths = []
    for path, rows in _hives(context):
        relative = context.get_relative_path(path)
        devices = {}
        for parts, name, data_type, data in rows:
            address = ''
            below = ()
            parent = parts
            for position, part in enumerate(parts):
                if _ADDRESS_KEY.match(part):
                    address = part.lower()
                    parent = parts[:position]
                    below = parts[position + 1:]
                    break
            named = _ADDRESS_VALUE.match(name)
            if not address and named:
                address = named.group(1).lower()
            if not address:
                continue
            row = devices.setdefault(address, [''] * 13 + [set()])
            row[1] = address
            row[13].add('\\'.join(parent))
            shown, _ = _render(data_type, data)
            if named or (not below and name == 'Key'):
                row[8] = 'Yes'
            if not below and name == 'PairTime':
                row[0] = _system_time(data)
            for folder, wanted, column in _DEVICE_FIELDS:
                if name == wanted and below == ((folder,) if folder else ()) and not row[column]:
                    row[column] = shown
        if devices:
            source_paths.append(path)
        for address in sorted(devices):
            row = devices[address]
            data_list.append(tuple(row[:13]) + (' | '.join(sorted(row[13])), relative))
    return data_headers, data_list, '\n'.join(source_paths)
