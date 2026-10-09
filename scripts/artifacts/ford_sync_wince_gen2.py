"""Ford SYNC on Windows CE, generation 2: the SQLite stores under UserData.

Generation 2 keeps text messages and the Wi-Fi network list in SQLite databases, where
generation 1 used the binary files that ford_sync_wince.py reads. The call list and log
files the two generations share are read by that module.

    UserData/SMS_<address>.db     table SMSstore, one database per handset
    UserData/WiFiList.db          table WiFiNetworkList
"""

import os
import re
import sqlite3
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "ford_sync_wince_gen2_text_messages": {
        "name": "Ford SYNC WinCE Gen2 - Text Messages",
        "description": "Rows of the text message store the module keeps for each handset, "
                       "with the message time, the address, name and body stored in each "
                       "row and the read status as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From the SMSstore table of UserData/SMS_<address>.db, one database per "
                 "handset. Tested on two SYNC Gen2 units, a 2014 Ford Edge SEL and a 2011 "
                 "Ford Explorer XLT, read from the file sets extracted from each unit's "
                 "flash image. The Edge held 49 messages in one database and the Explorer "
                 "held none. Message Time is the time column, stored as text with the "
                 "month first: across the 49 rows a value above 12 occurs 20 times in the "
                 "second position and never in the first. It has no time zone and is "
                 "written out as if it were UTC with no offset applied. The tested rows "
                 "ran from 2011 to 2014, so the reading is the unit's clock or the "
                 "handset's and which is not established here. Whether a row is a received "
                 "or a sent message is not recorded in a column. Read Status is the "
                 "readstatus column as stored and held 0 on every tested row; the Name "
                 "column was empty on every tested row. Handset Address is the twelve hex "
                 "digits in the file name, shown with colons; a database named with twelve "
                 "zeros was present and empty on both units. The SMS_CANNED databases "
                 "beside these hold the same 15 stock replies in every file on both units "
                 "and are not read. A row establishes that the module stored this text for "
                 "the handset. It does not establish who read or wrote it.",
        "paths": ('*/UserData/SMS_*.db*',),
        "sample_data": {
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 49 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "every SMSstore table was empty",
        },
        "output_types": "standard",
        "artifact_icon": "message-square",
    },
    "ford_sync_wince_gen2_wifi_networks": {
        "name": "Ford SYNC WinCE Gen2 - Wi-Fi Network List",
        "description": "Rows of the module's Wi-Fi network list, with the network name, "
                       "access point address, stored location text, signal strength and "
                       "priority of each network.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From the WiFiNetworkList table of UserData/WiFiList.db. Both tested SYNC "
                 "Gen2 units (a 2014 Ford Edge SEL and a 2011 Ford Explorer XLT) held the "
                 "table with no rows, so this artifact is written from the table's own "
                 "column names and has not been exercised on real rows. Columns are "
                 "reported as stored. The key material and key length columns are not "
                 "surfaced. A row would record that the module stored the network. It "
                 "would not establish that the vehicle was at the stored location.",
        "paths": ('*/UserData/WiFiList.db*',),
        "sample_data": {
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, "
                             "WiFiNetworkList was empty",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "WiFiNetworkList was empty",
        },
        "output_types": "standard",
        "artifact_icon": "wifi",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_SMS_NAME = re.compile(r'SMS_([0-9A-Fa-f]{12})\.db')


def _databases(context, wanted):
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        if not wanted(base) or base.endswith(('-journal', '-wal', '-shm')):
            continue
        try:
            with open(file_found, 'rb') as handle:
                if handle.read(16) != _SQLITE_MAGIC:
                    continue
        except OSError:
            continue
        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        try:
            yield file_found, db
        finally:
            db.close()


def _has_table(db, table):
    try:
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                          (table,)).fetchone() is not None
    except sqlite3.Error:
        return False


def _message_time(text):
    """'MM-DD-YYYY HH:MM:SS' as 'YYYY-MM-DD HH:MM:SS'; '' when it is anything else."""
    try:
        return datetime.strptime(str(text).strip(),
                                 '%m-%d-%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


@artifact_processor
def ford_sync_wince_gen2_text_messages(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: _SMS_NAME.match(name) is not None):
        if not _has_table(db, 'SMSstore'):
            continue
        source_paths.append(file_found)
        digits = _SMS_NAME.match(os.path.basename(file_found)).group(1).lower()
        address = ':'.join(digits[i:i + 2] for i in range(0, 12, 2))
        try:
            rows = db.execute(
                'SELECT time, address, name, body, readstatus FROM SMSstore').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Ford SYNC WinCE Gen2: could not read SMSstore: {ex}')
            continue
        for time_text, sender, name, body, read_status in rows:
            data_list.append((_message_time(time_text), sender or '', name or '', body or '',
                              read_status, address, context.get_relative_path(file_found)))

    data_headers = (('Message Time', 'datetime'), 'Address', 'Name', 'Message',
                    'Read Status (as stored)', 'Handset Address', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_gen2_wifi_networks(context):
    data_list = []
    source_paths = []
    for file_found, db in _databases(context, lambda name: name.startswith('WiFiList.db')):
        if not _has_table(db, 'WiFiNetworkList'):
            continue
        source_paths.append(file_found)
        try:
            rows = db.execute(
                'SELECT Ssid, MacAddr, GPSLocation, SignalStrength, Priority, Privacy, '
                'AuthMode FROM WiFiNetworkList').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Ford SYNC WinCE Gen2: could not read WiFiNetworkList: {ex}')
            continue
        for row in rows:
            data_list.append(tuple('' if value is None else value for value in row)
                             + (context.get_relative_path(file_found),))

    data_headers = ('Network Name', 'Access Point Address', 'Location Text (as stored)',
                    'Signal Strength (as stored)', 'Priority', 'Privacy (as stored)',
                    'Authentication Mode (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
