"""GM OnStar telematics module built by LG, generations 9 and 10.

Named for the module, not a vehicle brand: the same module is fitted across GM brands,
and the samples behind this file are Chevrolet, GMC and Buick vehicles. The two
generations keep different files under the same var/ tree:

    Generation 9   var/sysinfo/BT.dat         five fixed Bluetooth device slots
                   var/BTfeature/phoneNN.pb   one self-describing phonebook per slot
    Generation 10  var/sysinfo/*.dat          text files of [section] and key=value lines
    Both           var/log/poweroff.log       one line: a clock reading and two numbers
                   var/ver.txt                the software version

Generation 9 also has binary phone.dat, vifdata.dat and occ.dat files. They are raw
structures with no framing this module can check, and they are not read.
"""

import os
import re
import sqlite3
import struct
from datetime import datetime

from scripts.ilapfuncs import (artifact_processor, device_info, logfunc,
                               open_sqlite_db_readonly)

__artifacts_v2__ = {
    "gm_onstar_lg_bt_devices": {
        "name": "GM OnStar LG Gen9 - Bluetooth Devices",
        "description": "The Bluetooth device slots the telematics module stores, with the "
                       "device number, name and Bluetooth address held in each occupied slot.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/sysinfo/BT.dat. Tested on four generation 9 units: a 2012 Chevrolet "
                 "Cruze LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick "
                 "Enclave, read from the file sets extracted from each unit's flash image. The "
                 "file is 323 bytes: an 8-byte header, five 60-byte slots and a '<SysInfo' "
                 "tag, and a file without that shape is logged and not read. A slot with no "
                 "name and device number 0 is left out. The address is stored in three parts "
                 "and is assembled here as non-significant, upper and lower part. That "
                 "assembly is checked by the data: for all eight phonebook files on the two "
                 "units that had them, the address in the phonebook file's own header equalled "
                 "the address assembled for the slot with the same device number. Three units "
                 "held four occupied slots each and one held none. The eight bytes at the end "
                 "of each slot are not decoded. An extraction can hold several copies of one "
                 "file, marked (Deleted) or (CopyN) in the name. Files with identical content "
                 "are read once and Identical Files gives how many there were. A slot records "
                 "that the module held a pairing entry for the device. It does not establish "
                 "who carried it. Generation 10 units have no BT.dat.",
        "paths": ('*/var/sysinfo/BT.dat*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 4 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 4 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, BT.dat held no occupied slot",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 4 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "no BT.dat on generation 10",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, no BT.dat on "
                             "generation 10",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "gm_onstar_lg_phonebook": {
        "name": "GM OnStar LG Gen9 - Phonebook",
        "description": "Contacts in the phonebook file the telematics module keeps for each "
                       "Bluetooth device number, with the last name, first name and the home, "
                       "work, mobile and other numbers stored for each contact.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/BTfeature/phoneNN.pb, where NN is the device number of a slot in "
                 "BT.dat. Tested on four generation 9 units: a 2012 Chevrolet Cruze LT, a 2012 "
                 "GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave, read from "
                 "the file sets extracted from each unit's flash image. Two of them held "
                 "phonebook files, four each. The file starts with the signature GMPB and the "
                 "handset's address, then lists its own fields by id and name, then holds "
                 "records of (field id, length, value) entries. All eight tested files parsed "
                 "to their exact end under that layout, and a file that does not is logged and "
                 "not read. The field names are the file's own. Every tested file also "
                 "declared a seventh field, Call History Time Stamp, and no record used it, so "
                 "it has no column. A contact with two values for one field has them joined "
                 "with a semicolon. Handset Address is the address in the file header. An "
                 "extraction can hold several copies of one file, marked (Deleted) or (CopyN) "
                 "in the name. Files with identical content are read once and Identical Files "
                 "gives how many there were. A record establishes that the module held the "
                 "contact for that device. It does not establish that any number was dialled.",
        "paths": ('*/var/BTfeature/phone*.pb*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 244 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 1119 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, no phoneNN.pb file in the extracted set",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, no "
                             "phoneNN.pb file in the extracted set",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "no phoneNN.pb file in the extracted set",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, no phoneNN.pb file in "
                             "the extracted set",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "gm_onstar_lg_gps_reports": {
        "name": "GM OnStar LG Gen10 - GPS Reports",
        "description": "GPS reports the telematics module stored, with the UTC time, latitude "
                       "and longitude of each report and the elevation, speed, course, "
                       "dilution of precision and satellite count stored with it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From the GPSRegularReport sections of var/sysinfo/gps.dat, a text file of "
                 "[section] and key=value lines. Tested on two generation 10 units: a 2016 "
                 "Chevrolet Cruze and a 2017 Buick Encore. Each held ten reports. Timestamp is "
                 "built from the report's utc_year to utc_sec keys and is UTC: on all 20 "
                 "tested reports the report's own GPS week and time of week, converted to a "
                 "date, was exactly 18 seconds ahead of that reading, which is the GPS to UTC "
                 "offset in force since 2017. Latitude and Longitude are the stored eight-byte "
                 "values divided by 10,000,000. That scale is derived by comparison: on one "
                 "unit an independent parse of the same data gave positions for the same "
                 "timestamps, and they agreed to within 0.0000001 degree. Elevation, Speed "
                 "Over Ground and Course Over Ground are shown as stored because their units "
                 "are not established here; speed was 0 on all 20 reports. Reports whose "
                 "latitude and longitude are both zero are left out. File Save Time is the "
                 "TimeStamp in the file's first section, in the same clock. Report Number is "
                 "the section's number; on the tested units number 0 was the most recent. The "
                 "other keys of each report (variances, velocity vectors, fix flags) are not "
                 "surfaced. An extraction can hold several copies of one file, marked "
                 "(Deleted) or (CopyN) in the name. Files with identical content are read once "
                 "and Identical Files gives how many there were. A report records where the "
                 "module's receiver placed itself at that time. It does not establish who was "
                 "in the vehicle. Generation 9 units have a zero-byte obn/storage/gps file and "
                 "no gps.dat.",
        "paths": ('*/var/sysinfo/gps.dat*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, no gps.dat on generation 9",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 0 rows, no "
                             "gps.dat on generation 9",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, no gps.dat on generation 9",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, no "
                             "gps.dat on generation 9",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 10 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 10 rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "gm_onstar_lg_power_off_log": {
        "name": "GM OnStar LG - Power Off Log",
        "description": "Power-off records the telematics module wrote, one per poweroff.log "
                       "file, with the clock reading in the record and the two numbers that "
                       "follow it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/log/poweroff.log, a one-line file holding a date and time, a comma "
                 "and two numbers. Tested on four generation 9 units: a 2012 Chevrolet Cruze "
                 "LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave, "
                 "read from the file sets extracted from each unit's flash image. Tested on "
                 "two generation 10 units: a 2016 Chevrolet Cruze and a 2017 Buick Encore. "
                 "Across the six units all rows but one came from copies the acquisition "
                 "marked (Deleted), between 5 and 185 distinct ones per unit. The record does "
                 "not state a time zone. On the two generation 10 units the latest reading was "
                 "within three seconds of a GPS report whose time is UTC, so the clock is "
                 "consistent with UTC there; for generation 9 that is not established. "
                 "Readings of 1970-01-01 00:00:00 occur on three units and do not give a date. "
                 "The two numbers are shown as stored: the first was 1 on every tested row and "
                 "the second was 0 or 1, and nothing available here documents them. An "
                 "extraction can hold several copies of one file, marked (Deleted) or (CopyN) "
                 "in the name. Files with identical content are read once and Identical Files "
                 "gives how many there were. On one unit an independent parse reported the "
                 "same 185 times. A row records that the module wrote a power-off record with "
                 "that reading. What triggered it is not established.",
        "paths": ('*/var/log/poweroff.log*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 5 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 13 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 113 "
                             "rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 185 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "gm_onstar_lg_stored_values": {
        "name": "GM OnStar LG Gen10 - Stored Values",
        "description": "Selected values from the generation 10 module's text state files: the "
                       "redial and recall numbers, the module's own mobile numbers, "
                       "destination coordinates and text, stolen-vehicle and dealer values, "
                       "and the unit expiry date, each with the save time of the file it came "
                       "from.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/sysinfo/phone.dat, miscretlog.dat, occ.dat, bill.dat and "
                 "vifdata.dat, text files of [section] and key=value lines. Tested on two "
                 "generation 10 units: a 2016 Chevrolet Cruze and a 2017 Buick Encore. A row "
                 "is reported only when the key holds a value other than empty, 0 or -1, so "
                 "most keys give no row: the two units gave four rows each (the OTUBMgmnt "
                 "expiry year, month and day on both, a redial number on one and a lock-out "
                 "counter on the other). Section and Key are the file's own names and no "
                 "meaning beyond the name is established here. Values stored as hexadecimal "
                 "bytes are shown as text when they are printable ASCII. The destination, name "
                 "tag and recent destination lists were empty on both units; their numbered "
                 "sections are reported whole when present, and that path has not been "
                 "exercised on real data. File Save Time is the TimeStamp in the file's first "
                 "section; several files carried 1970 readings. Not surfaced: the diagnostic "
                 "trouble codes in dtc.dat, the data identifier tables in dpid.dat and "
                 "nondid.dat, the display device and customisation tables in vifdata.dat, the "
                 "authentication key in tcuid.dat, and the empty alerts.db. An extraction can "
                 "hold several copies of one file, marked (Deleted) or (CopyN) in the name. "
                 "Files with identical content are read once and Identical Files gives how "
                 "many there were. Files of the same name that do not open with the [*] "
                 "section are erased or partial copies and are not read.",
        "paths": ('*/var/sysinfo/*.dat*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, generation 9 files are not in the text format",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 0 rows, "
                             "generation 9 files are not in the text format",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, generation 9 files are not in the text format",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "generation 9 files are not in the text format",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 4 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 4 rows",
        },
        "output_types": "standard",
        "artifact_icon": "list",
    },
    "gm_onstar_lg_unit_info": {
        "name": "GM OnStar LG - Unit Information",
        "description": "Identifiers and versions the telematics module stores: the VIN, the "
                       "device id, the assembly label code, the software version lines and the "
                       "network interface address.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "One row per value with the file it came from. Tested on four generation 9 "
                 "units: a 2012 Chevrolet Cruze LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 "
                 "SLE and a 2011 Buick Enclave, read from the file sets extracted from each "
                 "unit's flash image. Tested on two generation 10 units: a 2016 Chevrolet "
                 "Cruze and a 2017 Buick Encore. Generation 9 gives the lines of var/ver.txt "
                 "and of the version file in var/fac that ver.txt names. Generation 10 gives "
                 "the lines of var/ver.txt, DevInfo/DevId, DevInfo/Ext/VIN, the VIN section of "
                 "vifdata.dat, the assembly label code of tcuid.dat and, where present, the "
                 "interface name and IP addresses in the keyval table of rr_db.dat (one unit). "
                 "The VIN is what the module stored, and a module moved between vehicles could "
                 "carry an earlier one. Generation 9 keeps its VIN in a binary vifdata.dat "
                 "that this module does not read. Values are reported as stored.",
        "paths": (
            '*/var/ver.txt*',
            '*/var/fac/ver_*.txt*',
            '*/DevInfo/DevId*',
            '*/DevInfo/Ext/VIN*',
            '*/var/sysinfo/vifdata.dat*',
            '*/var/sysinfo/tcuid.dat*',
            '*/var/sysinfo/rr_db.dat*',
        ),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 6 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 6 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 7 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 9 rows",
        },
        "output_types": "standard",
        "artifact_icon": "info",
    },
}

_BT_FILE_SIZE = 323
_BT_SLOTS = 5
_BT_SLOT_SIZE = 60
_PB_FIELD_NAMES = ('Last Name', 'First Name', 'Home Number', 'Work Number',
                   'Mobile Number', 'Other Number')
_HEX_BYTES = re.compile(r'(?:[0-9A-Fa-f]{2} )*[0-9A-Fa-f]{2}')
_SECTION = re.compile(r'\[(.+)\]')
_POWER_LINE = re.compile(r'([A-Z][a-z]{2} [A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \d{4}),'
                         r'(-?\d+),(-?\d+)')
# Sections and keys of the generation 10 text files worth a row when they hold a value.
_STORED_KEYS = {
    'phone.dat': (('RedialNum', 'PhoneNumber'), ('RecallNum', 'PhoneNumber'),
                  ('NameTagList', 'NumOfNametag'), ('DestinationList', 'NumOfDestination'),
                  ('IMSAPNLockOutInfo', 'LockOutCounter')),
    'miscretlog.dat': (('NAD', 'MDN'), ('NAD', 'MIN'), ('OBNDestContext', 'Latitude'),
                       ('OBNDestContext', 'Longitude'), ('OBNDestContext', 'StreetNumber'),
                       ('OBNDestContext', 'StreetText'),
                       ('OBNDestContext', 'CrossStreetText'), ('OBNDestContext', 'POIText'),
                       ('OBNRecentDestList', 'TotalDestListNum')),
    'occ.dat': (('PacketInfo', 'DestLatitude'), ('PacketInfo', 'DestLongitude'),
                ('PacketInfo', 'DestURI'), ('TheftRecord', 'TheftActive')),
    'bill.dat': (('OTUBMgmnt', 'ExpireYear'), ('OTUBMgmnt', 'ExpireMonth'),
                 ('OTUBMgmnt', 'ExpireDay'), ('OTUBMgmnt', 'TotalUnits')),
    'vifdata.dat': (('DEAMgmnt', 'Name'), ('DEAMgmnt', 'PhoneNum'), ('DEAMgmnt', 'Address'),
                    ('DEAMgmnt', 'StreetName'), ('DEAMgmnt', 'CityName'),
                    ('DEAMgmnt', 'State')),
}
# Numbered sections reported whole when present; none held rows on the tested units.
_LIST_SECTIONS = re.compile(r'^(OBNRecentDestList|NameTagList|DestinationList)\d+')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return b''


def _base_name(path):
    """The file name without the '(Deleted)' and '(CopyN)' marks an acquisition adds."""
    return re.sub(r'\((?:Deleted|Copy\d+)\)', '', os.path.basename(path))


def _distinct(paths):
    """(path, data, copies) for each distinct content among paths, in path order."""
    seen = {}
    for path in paths:
        data = _read(path)
        if not data:
            continue
        if data in seen:
            seen[data][1] += 1
        else:
            seen[data] = [path, 1]
    return [(path, data, copies) for data, (path, copies) in seen.items()]


def _address(raw):
    return ':'.join(f'{byte:02x}' for byte in raw)


# ---------------------------------------------------------------------------
# Generation 9: Bluetooth slots and phonebooks
# ---------------------------------------------------------------------------

def _parse_bt(data):
    """Slots of a BT.dat as (slot, device number, name, address), or None if unframed.

    The file is 323 bytes: an 8-byte header, five 60-byte slots and a '<SysInfo' tag.
    A slot stores the address as a four-byte lower part, a one-byte upper part and a
    two-byte non-significant part, big-endian, followed by a two-byte device number and
    the name.
    """
    tag_offset = 8 + _BT_SLOTS * _BT_SLOT_SIZE
    if len(data) != _BT_FILE_SIZE or not data[tag_offset:].startswith(b'<SysInfo'):
        return None
    slots = []
    for slot in range(_BT_SLOTS):
        record = data[8 + slot * _BT_SLOT_SIZE:8 + (slot + 1) * _BT_SLOT_SIZE]
        name = record[22:52].split(b'\x00', 1)[0].decode('utf-8', 'replace')
        number = struct.unpack('>H', record[20:22])[0]
        if not name and not number:
            continue
        address = record[18:20] + record[16:17] + record[13:16]
        slots.append((slot, number, name, _address(address)))
    return slots


@artifact_processor
def gm_onstar_lg_bt_devices(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'BT.dat']
    for file_found, data, copies in _distinct(files):
        slots = _parse_bt(data)
        if slots is None:
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} does not have the '
                    'Bluetooth slot layout, not read')
            continue
        source_paths.append(file_found)
        for slot, number, name, address in slots:
            data_list.append((number, name, address, slot, copies,
                              context.get_relative_path(file_found)))

    data_headers = ('Device Number', 'Device Name', 'Bluetooth Address', 'Slot',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _parse_pb(data):
    """(address, records) from a GMPB phonebook, or None when the framing does not hold.

    After a 16-byte header the file lists its fields (an id byte and a NUL-terminated
    name each), then records: a length byte followed by (field id, length, value)
    triples that must fill the record exactly.
    """
    if len(data) < 17 or data[:4] != b'GMPB':
        return None
    address = _address(data[6:12])
    offset = 17
    fields = {}
    try:
        for _ in range(data[16]):
            field_id = data[offset]
            end = data.index(b'\x00', offset + 1)
            fields[field_id] = data[offset + 1:end].decode('utf-8', 'replace')
            offset = end + 1
    except (IndexError, ValueError):
        return None
    if not fields:
        return None
    records = []
    while offset < len(data):
        length = data[offset]
        body = data[offset + 1:offset + 1 + length]
        if not length or len(body) != length:
            return None
        pos = 0
        record = {}
        while pos < length:
            if pos + 2 > length:
                return None
            field_id, size = body[pos], body[pos + 1]
            if field_id not in fields or pos + 2 + size > length:
                return None
            record.setdefault(fields[field_id], []).append(body[pos + 2:pos + 2 + size])
            pos += 2 + size
        records.append(record)
        offset += 1 + length
    return address, records


def _field(record, name):
    values = record.get(name, [])
    return '; '.join(value.decode('utf-8', 'replace') for value in values)


@artifact_processor
def gm_onstar_lg_phonebook(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context)
             if re.fullmatch(r'phone\d+\.pb', _base_name(f))]
    for file_found, data, copies in _distinct(files):
        parsed = _parse_pb(data)
        if parsed is None:
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} does not have the GMPB '
                    'framing, not read')
            continue
        source_paths.append(file_found)
        address, records = parsed
        number = int(re.search(r'phone(\d+)\.pb', _base_name(file_found)).group(1))
        for position, record in enumerate(records, start=1):
            data_list.append((number, address) + tuple(
                _field(record, name) for name in _PB_FIELD_NAMES) + (
                    position, copies, context.get_relative_path(file_found)))

    data_headers = ('Device Number', 'Handset Address', 'Last Name', 'First Name',
                    'Home Number', 'Work Number', 'Mobile Number', 'Other Number',
                    'Record Number',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Generation 10: sectioned text files
# ---------------------------------------------------------------------------

def _parse_sections(data):
    """Sections of a generation 10 .dat file as {section: {key: value}}, or None.

    The file is CRLF text that opens with a [*] section holding TimeStamp and Version.
    Anything that does not open that way is not this format and is refused.
    """
    if not data.startswith(b'[*]\r\n'):
        return None
    sections = {}
    name = None
    for line in data.decode('latin-1').split('\r\n'):
        match = _SECTION.fullmatch(line)
        if match:
            name = match.group(1)
            sections.setdefault(name, {})
        elif name is not None and '=' in line and not line.startswith('\x1a'):
            key, value = line.split('=', 1)
            sections[name][key] = value
    if 'TimeStamp' not in sections.get('*', {}):
        return None
    return sections


def _save_time(sections):
    """The [*] TimeStamp ('MM-DD-YY HH:MM:SS') as 'YYYY-MM-DD HH:MM:SS', or ''."""
    try:
        return datetime.strptime(sections['*']['TimeStamp'].strip(),
                                 '%m-%d-%y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    except (KeyError, ValueError):
        return ''


def _hex_value(text):
    if _HEX_BYTES.fullmatch(text or ''):
        return bytes.fromhex(text.replace(' ', ''))
    return None


def _number(text, fmt):
    raw = _hex_value(text)
    if raw is None or len(raw) != struct.calcsize(fmt):
        return None
    return struct.unpack(fmt, raw)[0]


def _sectioned_files(context, name=None):
    files = [f for f in _regular_files(context)
             if (_base_name(f) == name if name else _base_name(f).endswith('.dat'))]
    for file_found, data, copies in _distinct(files):
        sections = _parse_sections(data)
        if sections is not None:
            yield file_found, sections, copies


@artifact_processor
def gm_onstar_lg_gps_reports(context):
    data_list = []
    source_paths = []
    for file_found, sections, copies in _sectioned_files(context, 'gps.dat'):
        found = False
        for section, values in sections.items():
            index = re.fullmatch(r'GPSRegularReport(\d+)', section)
            if not index:
                continue
            latitude = _number(values.get('lat'), '<d')
            longitude = _number(values.get('lon'), '<d')
            if latitude is None or longitude is None or not (latitude or longitude):
                continue
            seconds = _number(values.get('utc_sec'), '<f')
            try:
                stamp = datetime(int(values['utc_year']), int(values['utc_month']),
                                 int(values['utc_day']), int(values['utc_hour']),
                                 int(values['utc_min']),
                                 int(seconds or 0)).strftime('%Y-%m-%d %H:%M:%S')
            except (KeyError, ValueError, OverflowError):
                stamp = ''
            found = True
            data_list.append((
                stamp, round(latitude / 1e7, 7), round(longitude / 1e7, 7),
                values.get('elevation', ''), _number(values.get('sog'), '<f'),
                _number(values.get('cog'), '<f'), _number(values.get('hdop'), '<f'),
                values.get('sv_used_cnt', ''), values.get('gps_week', ''),
                values.get('gps_tow', ''), int(index.group(1)), _save_time(sections),
                copies, context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'Elevation (as stored)', 'Speed Over Ground (as stored)',
                    'Course Over Ground (as stored)', 'HDOP', 'Satellites Used',
                    'GPS Week', 'GPS Time Of Week (as stored)', 'Report Number',
                    ('File Save Time', 'datetime'), 'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _display(value):
    """A stored value for display: hex byte strings become text when they are text."""
    raw = _hex_value(value)
    if raw is None or ' ' not in value:
        return value.strip()
    stripped = raw.rstrip(b'\x00')
    if not stripped:
        return ''
    try:
        text = stripped.decode('ascii')
    except UnicodeDecodeError:
        return value
    return text if text.isprintable() else value


@artifact_processor
def gm_onstar_lg_stored_values(context):
    data_list = []
    source_paths = []
    for file_found, sections, copies in _sectioned_files(context):
        base = _base_name(file_found)
        rows = []
        for section, key in _STORED_KEYS.get(base, ()):
            value = _display(sections.get(section, {}).get(key, ''))
            if value and value not in ('0', '-1'):
                rows.append((section, key, value))
        for section, values in sections.items():
            if _LIST_SECTIONS.match(section):
                rows.extend((section, key, _display(value)) for key, value in values.items()
                            if _display(value))
        if rows:
            source_paths.append(file_found)
        for section, key, value in rows:
            data_list.append((_save_time(sections), base, section, key, value, copies,
                              context.get_relative_path(file_found)))

    data_headers = (('File Save Time', 'datetime'), 'File', 'Section', 'Key', 'Value',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Both generations
# ---------------------------------------------------------------------------

@artifact_processor
def gm_onstar_lg_power_off_log(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'poweroff.log']
    for file_found, data, copies in _distinct(files):
        found = False
        for match in _POWER_LINE.finditer(data.decode('latin-1')):
            try:
                stamp = datetime.strptime(' '.join(match.group(1).split()),
                                          '%a %b %d %H:%M:%S %Y')
            except ValueError:
                continue
            found = True
            data_list.append((stamp.strftime('%Y-%m-%d %H:%M:%S'), int(match.group(2)),
                              int(match.group(3)), copies,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Power Off Time', 'datetime'), 'Second Field (as stored)',
                    'Third Field (as stored)', 'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_onstar_lg_unit_info(context):
    data_list = []
    source_paths = []

    def add(label, value, file_found):
        value = str(value).strip().strip('\x00')
        if not value:
            return
        relative = context.get_relative_path(file_found)
        data_list.append((label, value, relative))
        if file_found not in source_paths:
            source_paths.append(file_found)
        device_info('GM OnStar LG', label, value, relative)

    groups = {}
    for file_found in _regular_files(context):
        groups.setdefault(_base_name(file_found), []).append(file_found)
    # ver.txt can hold the path of the version file in var/fac that is in effect.
    named = set()
    for file_found in groups.get('ver.txt', []):
        named.update(re.findall(r'ver_\w+\.txt', _read(file_found).decode('latin-1')))
    for base, files in sorted(groups.items()):
        if base == 'rr_db.dat':
            for file_found in files:
                if _read(file_found)[:16] != b'SQLite format 3\x00':
                    continue
                db = open_sqlite_db_readonly(file_found)
                if db is None:
                    continue
                try:
                    rows = db.execute("SELECT key, value FROM keyval WHERE key IN "
                                      "('IFNAME', 'IP4ADDR', 'IP6ADDR')").fetchall()
                except sqlite3.Error:
                    rows = []
                db.close()
                for key, value in rows:
                    add(f'Network {key}', value or '', file_found)
            continue
        for file_found, data, _copies in _distinct(files):
            if base == 'ver.txt' or base in named:
                for line in data.decode('latin-1').splitlines():
                    add(f'Version File Line ({base})', line, file_found)
            elif base == 'DevId':
                add('Device ID', data.decode('latin-1'), file_found)
            elif base == 'VIN':
                add('VIN (DevInfo)', data.decode('latin-1'), file_found)
            elif base in ('vifdata.dat', 'tcuid.dat'):
                sections = _parse_sections(data)
                if sections is None:
                    continue
                if base == 'vifdata.dat':
                    add('VIN (vifdata)', _display(sections.get('VIN', {}).get('VIN', '')),
                        file_found)
                else:
                    add('Assembly Label Code',
                        sections.get('TcuID', {}).get('AssyLabel.Code', ''), file_found)

    data_headers = ('Property', 'Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
