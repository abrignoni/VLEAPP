"""Ford Sync Gen3 Bluetooth phonebook, call history and paired-device records.

The head unit keeps these in two extension-less SQLite stores under BT/ on the user
data partition: btpbk (phonebook and call lists) and btpersist (paired devices and
their settings). Both are numbered per paired handset, slots 1 to 12.
"""

import os
import sqlite3

from scripts.ilapfuncs import artifact_processor, open_sqlite_db_readonly


__artifacts_v2__ = {
    "ford_sync_bt_contacts": {
        "name": "Bluetooth Phonebook",
        "description": "Contacts the head unit downloaded from each paired handset, with "
                       "the names, the phone numbers the record carried, email and postal "
                       "address as stored. One row per contact per handset slot.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-30",
        "last_update_date": "2026-08-30",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the PhoneBook<N> tables of BT/btpbk, an extension-less SQLite store "
                 "on the user data partition. The unit numbers its tables per paired "
                 "handset, slots 1 to 12, and the slot is reported so contacts from "
                 "different handsets stay separable. A phonebook entry records what the "
                 "unit downloaded over Bluetooth; it does not establish that any number was "
                 "dialled or that the handset owner was present. TelType is not surfaced "
                 "because nothing available here documents its values. The store carries no "
                 "write-ahead log or journal on the tested unit.",
        "paths": ('*/BT/btpbk*',),
        "sample_data": {
            "adams_ford_syncgen3": "Ford Sync Gen3 | 507 rows",
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows, BT/btpbk not present",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "ford_sync_bt_calls": {
        "name": "Bluetooth Call History",
        "description": "Calls the head unit recorded for each paired handset, with the time "
                       "as stored, the direction, and the name and number the record "
                       "carried.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-30",
        "last_update_date": "2026-08-30",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the Combined<N> tables of BT/btpbk, which the unit maintains "
                 "alongside separate InCall<N>, DialCall<N> and MissCall<N> tables. "
                 "Combined is read because it is the union of the three: on the tested unit "
                 "the two populated handsets gave 22+23+25=70 and 20+19+17=56, matching "
                 "their Combined row counts exactly. Direction is decoded from CallType, "
                 "and that mapping was derived from the data rather than assumed: filtering "
                 "Combined by each CallType produced a (number, date, time) row set "
                 "identical to the correspondingly named table, on both handsets "
                 "independently, giving 1 Received, 2 Dialled, 4 Missed. Any other value is "
                 "reported as stored. The unit writes the time as six separate text "
                 "components and records no timezone anywhere in the store, so the "
                 "timestamp is assembled as written and no conversion is applied. A call "
                 "record is what the handset reported to the unit over Bluetooth; it does "
                 "not establish who used the handset or that the vehicle was moving.",
        "paths": ('*/BT/btpbk*',),
        "sample_data": {
            "adams_ford_syncgen3": "Ford Sync Gen3 | 126 rows",
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows, BT/btpbk not present",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "ford_sync_bt_paired_devices": {
        "name": "Bluetooth Paired Devices",
        "description": "Handsets currently paired with the head unit, with the name, model, "
                       "manufacturer, network name, software version, Bluetooth address and "
                       "subscriber number the unit stored for each.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-30",
        "last_update_date": "2026-08-30",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From PairedDevInfo in BT/btpersist, joined to DeviceOrder and "
                 "HFPdeviceOrder on DeviceID for the primary-device flags, which are "
                 "reported as stored because nothing available here documents their values. "
                 "This table holds the pairings the unit currently retains, which is a "
                 "narrower set than the handsets it has ever seen: the devlog_*.txt files "
                 "in the same BT directory, which btDevices.py parses, covered five "
                 "handsets on the tested unit while this table held two. Read both. Class "
                 "of device, vendor id and product id are reported as stored.",
        "paths": ('*/BT/btpersist*',),
        "sample_data": {
            "adams_ford_syncgen3": "Ford Sync Gen3 | 2 rows",
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows, BT/btpersist not present",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
}



# Slots the head unit numbers its per-handset tables with.
DEVICE_SLOTS = range(1, 13)

# Proven on the tested unit, not assumed: for both populated handsets the
# (TelNum, Date, Time) row set of Combined<N> filtered to each CallType was identical
# to the row set of the correspondingly named table the unit maintains alongside it.
CALL_TYPES = {
    1: 'Received',   # matched InCall<N>
    2: 'Dialled',    # matched DialCall<N>
    4: 'Missed',     # matched MissCall<N>
}


def _tables(db):
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _stamp(row):
    """Build 'YYYY-MM-DD HH:MM:SS' from the six text components the unit stores.

    Returns '' when any component is missing, rather than inventing a partial time.
    No timezone is recorded anywhere in the store, so nothing is converted.
    """
    yyyy, mm, dd, hh, mi, ss = (str(v or '').strip() for v in row)
    if not (yyyy and mm and dd):
        return ''
    return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)} {hh.zfill(2)}:{mi.zfill(2)}:{ss.zfill(2)}"


def _btpbk_files(context):
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        if os.path.basename(file_found).lower().startswith('btpbk'):
            yield file_found


def _btpersist_files(context):
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        if os.path.basename(file_found).lower().startswith('btpersist'):
            yield file_found


@artifact_processor
def ford_sync_bt_contacts(context):
    data_list = []
    source_paths = []
    for file_found in _btpbk_files(context):
        try:
            db = open_sqlite_db_readonly(file_found)
        except sqlite3.Error:
            continue
        present = _tables(db)
        read_any = False
        for slot in DEVICE_SLOTS:
            table = f'PhoneBook{slot}'
            if table not in present:
                continue
            try:
                rows = db.execute(
                    f'SELECT RecId, FirstName, LastName, SortName, Email, '
                    f'TelNum0, TelNum1, TelNum2, TelNum3, TelNum4, TelNum5, '
                    f'TelNum6, TelNum7, TelNum8, StreetAdr0, Locality0, Region0, '
                    f'POCode0, Country0 FROM "{table}"').fetchall()
            except sqlite3.Error:
                continue
            read_any = True
            for r in rows:
                numbers = [str(n).strip() for n in r[5:14] if str(n or '').strip()]
                address = ', '.join(str(v).strip() for v in r[14:19]
                                    if str(v or '').strip())
                data_list.append((
                    slot, r[2] or '', r[1] or '', r[3] or '',
                    numbers[0] if numbers else '',
                    ', '.join(numbers[1:]), len(numbers), r[4] or '', address,
                    context.get_relative_path(file_found)))
        db.close()
        if read_any:
            source_paths.append(file_found)

    data_headers = ('Device Slot', 'Last Name', 'First Name', 'Sort Name',
                    'Phone Number', 'Other Numbers', 'Number Count', 'Email',
                    'Address', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_bt_calls(context):
    data_list = []
    source_paths = []
    for file_found in _btpbk_files(context):
        try:
            db = open_sqlite_db_readonly(file_found)
        except sqlite3.Error:
            continue
        present = _tables(db)
        read_any = False
        for slot in DEVICE_SLOTS:
            table = f'Combined{slot}'
            if table not in present:
                continue
            try:
                rows = db.execute(
                    f'SELECT Date_YYYY, Date_MM, Date_DD, Time_hh, Time_min, Time_sec, '
                    f'CallType, SortName, TelNum, TelType, RecId '
                    f'FROM "{table}"').fetchall()
            except sqlite3.Error:
                continue
            read_any = True
            for r in rows:
                direction = CALL_TYPES.get(r[6], f'{r[6]} (as stored)')
                data_list.append((
                    _stamp(r[0:6]), direction, r[7] or '', r[8] or '',
                    r[9], slot, r[10],
                    context.get_relative_path(file_found)))
        db.close()
        if read_any:
            source_paths.append(file_found)

    data_headers = (('Call Time', 'datetime'), 'Direction', 'Name',
                    'Phone Number', 'Number Type (as stored)', 'Device Slot',
                    'Record ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_bt_paired_devices(context):
    data_list = []
    source_paths = []
    for file_found in _btpersist_files(context):
        try:
            db = open_sqlite_db_readonly(file_found)
        except sqlite3.Error:
            continue
        present = _tables(db)
        if 'PairedDevInfo' not in present:
            db.close()
            continue

        primary = {}
        if 'DeviceOrder' in present:
            try:
                primary = {r[0]: r[1] for r in
                           db.execute('SELECT DeviceID, primaryDevice FROM DeviceOrder')}
            except sqlite3.Error:
                primary = {}
        hfp_primary = {}
        if 'HFPdeviceOrder' in present:
            try:
                hfp_primary = {r[0]: r[1] for r in db.execute(
                    'SELECT HFPdeviceID, HFPprimaryDevice FROM HFPdeviceOrder')}
            except sqlite3.Error:
                hfp_primary = {}

        try:
            rows = db.execute(
                'SELECT DeviceID, DeviceName, DeviceModel, ManufacturerName, '
                'NetworkName, DeviceSoftwareVersion, DeviceAddress, subscriberNum, '
                'ClassOfDevice, VendorId, ProductId FROM PairedDevInfo').fetchall()
        except sqlite3.Error:
            db.close()
            continue
        db.close()
        source_paths.append(file_found)
        for r in rows:
            data_list.append((
                r[0], r[1] or '', r[2] or '', r[3] or '', r[4] or '',
                r[5] or '', r[6] or '', r[7] or '', r[8] or '',
                primary.get(r[0], ''), hfp_primary.get(r[0], ''),
                r[9], r[10], context.get_relative_path(file_found)))

    data_headers = ('Device Slot', 'Device Name', 'Model', 'Manufacturer',
                    'Network Name', 'Device Software Version', 'Bluetooth Address',
                    'Subscriber Number', 'Class of Device (as stored)',
                    'Primary Device (as stored)', 'HFP Primary (as stored)',
                    'Vendor ID (as stored)', 'Product ID (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
