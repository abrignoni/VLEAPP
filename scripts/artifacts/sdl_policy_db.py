"""SmartDeviceLink policy database and application resumption file.

Named for the component, not a vehicle: the app-link component of a head unit keeps these
under a storage/sdl folder, and the samples behind this file are a Ford SYNC Gen3 module
and a Ford SYNC 4 module.

    storage/sdl/policy         SQLite: device, app_level, consent_group, nickname,
                               module_meta, module_config and the policy tables
    storage/sdl/app_info.dat   JSON: the last ignition-off time and the applications
                               kept for resumption

The policy text itself (functional groups, rpc lists, messages, endpoints) is the same
on every unit that received it and is not reported. ford_sync_policy_table.py reads the
JSON snapshots of the same policy table that another generation keeps.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "sdl_policy_devices": {
        "name": "SDL Policy - Devices",
        "description": "Rows of the policy database's device table: the stored device "
                       "identifier with the hardware, operating system, version and carrier "
                       "text recorded for it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SDL Policy",
        "notes": "From the SQLite policy database storage/sdl/policy that the head unit's "
                 "app-link component keeps. Tested on two units: a 2018 Ford Expedition (SYNC "
                 "Gen3) read from its export and a Ford SYNC 4 unit read from its logical zip. "
                 "The SYNC Gen3 unit held 10 device rows and the SYNC 4 unit none. Seven of "
                 "the ten carried hardware, operating system, version and carrier text, and "
                 "the operating system was iOS on all seven; three rows held only the "
                 "identifier. Firmware revision and connection type were empty on every tested "
                 "row. Unpaired was 1 on one row and 0 on nine, as stored. Device ID is a "
                 "64-character value the component stores for the device; it is not resolved "
                 "to a name or an address here. A row records that the component registered a "
                 "device that reported those values. It does not establish whose device it "
                 "was.",
        "paths": ('*/sdl/policy',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 10 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, the device table is "
                                   "empty",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "sdl_policy_app_usage": {
        "name": "SDL Policy - Application Usage",
        "description": "Rows of the policy database's application usage table: the application "
                       "id, the nicknames and types the policy lists for it, and the minutes "
                       "and counts the component tallied.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SDL Policy",
        "notes": "From the SQLite policy database storage/sdl/policy that the head unit's "
                 "app-link component keeps. Tested on two units: a 2018 Ford Expedition (SYNC "
                 "Gen3) read from its export and a Ford SYNC 4 unit read from its logical zip. "
                 "The SYNC Gen3 unit held six rows and the SYNC 4 unit none. Minutes and "
                 "counts are the component's own tallies, as stored; one tested application "
                 "had 63 minutes in the full level and 14 user selections, and the others had "
                 "none or one. Policy Nicknames are the names the policy table lists for that "
                 "application id, joined with a bar: they come from the policy, not from the "
                 "device, and one id can carry several. What each HMI level means is not "
                 "documented here. A row records the component's tally for an application. It "
                 "does not establish who used it.",
        "paths": ('*/sdl/policy',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 6 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, the application usage "
                                   "table is empty",
        },
        "output_types": "standard",
        "artifact_icon": "bar-chart-2",
    },
    "sdl_policy_consents": {
        "name": "SDL Policy - Consent Records",
        "description": "Consent records of the policy database: the functional group, the "
                       "consent value and input, the application and device identifiers and "
                       "the stored time stamp.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SDL Policy",
        "notes": "From the SQLite policy database storage/sdl/policy that the head unit's "
                 "app-link component keeps. Tested on two units: a 2018 Ford Expedition (SYNC "
                 "Gen3) read from its export and a Ford SYNC 4 unit read from its logical zip. "
                 "The SYNC Gen3 unit held eight records, seven for an application on a device "
                 "and one for a device alone, all dated 2021, all with consent value 1 and "
                 "input GUI; the SYNC 4 unit held none. The time stamp is text ending in Z and "
                 "is reported as the row states it. Functional Group is the policy's name for "
                 "the group of functions consented to, as stored. Device ID is a 64-character "
                 "value the component stores for the device; it is not resolved to a name or "
                 "an address here. A record shows that consent was entered on the unit's "
                 "screen at that time. It does not establish who entered it.",
        "paths": ('*/sdl/policy',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 8 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows, the consent tables are "
                                   "empty",
        },
        "output_types": "standard",
        "artifact_icon": "check-square",
    },
    "sdl_policy_module_values": {
        "name": "SDL Policy - Module Values",
        "description": "The values the policy database holds about the module itself: identity "
                       "and exchange counters, vehicle make, model and year, and the module's "
                       "usage and error counts.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SDL Policy",
        "notes": "From the SQLite policy database storage/sdl/policy that the head unit's "
                 "app-link component keeps. Tested on two units: a 2018 Ford Expedition (SYNC "
                 "Gen3) read from its export and a Ford SYNC 4 unit read from its logical zip. "
                 "Each gave 21 rows. Rows are the columns of the module_meta, module_config "
                 "and usage_and_error_count tables, one per column, with the table and column "
                 "names as stored; the certificate column is left out. They include the VIN, a "
                 "software version, the ignition cycles since the last policy exchange, the "
                 "odometer value at that exchange and a count of days after an epoch, which is "
                 "shown as stored and not converted. On the SYNC 4 unit the vehicle make, "
                 "model and year were empty. The policy text itself (functional groups, rpc "
                 "lists, messages, endpoints) is not reported because it is not the unit's own "
                 "state.",
        "paths": ('*/sdl/policy',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 21 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 21 rows",
        },
        "output_types": "standard",
        "artifact_icon": "file-text",
    },
    "sdl_app_resumption": {
        "name": "SDL - Application Resumption Data",
        "description": "The app-link component's resumption file: the last ignition-off time "
                       "it stores and, for each application kept for resumption, its time "
                       "stamp, application and device identifiers, level and ignition-off "
                       "count.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SDL Policy",
        "notes": "From storage/sdl/app_info.dat, a JSON file. Tested on two units: a 2018 Ford "
                 "Expedition (SYNC Gen3) read from its export, which gave 17 rows, and a Ford "
                 "SYNC 4 unit read from its logical zip, which gave one. The first row of a "
                 "file is its last_ign_off_time; the others are the entries of its application "
                 "list, which was empty on the SYNC 4 unit. Times are whole seconds since 1970 "
                 "and are written out with no offset applied; the stored number is shown "
                 "beside each. On the SYNC Gen3 unit the application time stamps run from 2019 "
                 "to 2023 and the last ignition-off time is in 2026. Seven of the eight device "
                 "identifiers in the list are also in the policy database's device table. "
                 "Device ID is a 64-character value the component stores for the device; it is "
                 "not resolved to a name or an address here. Level, ignition-off count and the "
                 "media flag are shown as stored. A row records that the component kept that "
                 "application's state for a device. It does not establish that the application "
                 "was in use at the time stamp.",
        "paths": ('*/sdl/app_info.dat',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | 17 "
                                       "rows",
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "rotate-cw",
    },
}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_MODULE_TABLES = ('module_meta', 'module_config', 'usage_and_error_count')
_NOT_REPORTED = ('certificate',)
_USAGE_COLUMNS = ('minutes_in_hmi_full', 'minutes_in_hmi_limited', 'minutes_in_hmi_background',
                  'minutes_in_hmi_none', 'count_of_user_selections',
                  'count_of_rejected_rpcs_calls', 'count_of_rpcs_sent_in_hmi_none',
                  'app_registration_language_gui', 'app_registration_language_vui')


def _policies(context):
    """(path, relative path, connection) for each matched policy database."""
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found) or os.path.basename(file_found) != 'policy':
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
            yield file_found, context.get_relative_path(file_found), db
        finally:
            db.close()


def _table(db, table):
    """Rows of a table as dicts; [] when the table is missing or unreadable."""
    try:
        cursor = db.execute(f'SELECT * FROM "{table}"')
    except sqlite3.Error:
        return []
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _text(value):
    return '' if value is None else value


def _stamp(text):
    """A stored 'YYYY-MM-DDThh:mm:ssZ' time as report text; '' when it is not one."""
    try:
        return datetime.strptime(str(text), '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


@artifact_processor
def sdl_policy_devices(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _policies(context):
        rows = _table(db, 'device')
        if rows:
            source_paths.append(file_found)
        for row in rows:
            data_list.append((_text(row.get('id')), _text(row.get('hardware')),
                              _text(row.get('os')), _text(row.get('os_version')),
                              _text(row.get('carrier')), _text(row.get('firmware_rev')),
                              _text(row.get('connection_type')), _text(row.get('unpaired')),
                              relative))

    data_headers = ('Device ID (as stored)', 'Hardware', 'OS', 'OS Version', 'Carrier',
                    'Firmware Revision', 'Connection Type', 'Unpaired (as stored)',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def sdl_policy_app_usage(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _policies(context):
        rows = _table(db, 'app_level')
        names = {}
        for row in _table(db, 'nickname'):
            names.setdefault(row.get('application_id'), []).append(_text(row.get('name')))
        kinds = {}
        for row in _table(db, 'app_type'):
            kinds.setdefault(row.get('application_id'), []).append(_text(row.get('name')))
        if rows:
            source_paths.append(file_found)
        for row in rows:
            app = row.get('application_id')
            data_list.append((_text(app), ' | '.join(names.get(app, [])),
                              ' | '.join(kinds.get(app, [])))
                             + tuple(_text(row.get(column)) for column in _USAGE_COLUMNS)
                             + (relative,))

    data_headers = ('Application ID', 'Policy Nicknames', 'Policy Application Types',
                    'Minutes In HMI Full', 'Minutes In HMI Limited',
                    'Minutes In HMI Background', 'Minutes In HMI None', 'User Selections',
                    'Rejected RPC Calls', 'RPCs Sent In HMI None', 'Registration Language GUI',
                    'Registration Language VUI', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def sdl_policy_consents(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _policies(context):
        rows = [(row, 'Application') for row in _table(db, 'consent_group')] \
            + [(row, 'Device') for row in _table(db, 'device_consent_group')]
        if rows:
            source_paths.append(file_found)
        for row, kind in rows:
            data_list.append((_stamp(row.get('time_stamp')), kind,
                              _text(row.get('functional_group_id')),
                              _text(row.get('is_consented')), _text(row.get('input')),
                              _text(row.get('application_id')), _text(row.get('device_id')),
                              _text(row.get('time_stamp')), relative))

    data_headers = (('Consent Time', 'datetime'), 'Record Kind', 'Functional Group',
                    'Consented (as stored)', 'Input', 'Application ID',
                    'Device ID (as stored)', 'Time Stamp (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def sdl_policy_module_values(context):
    data_list = []
    source_paths = []
    for file_found, relative, db in _policies(context):
        found = False
        for table in _MODULE_TABLES:
            for row in _table(db, table):
                for column, value in row.items():
                    if column in _NOT_REPORTED:
                        continue
                    found = True
                    data_list.append((table, column, _text(value), relative))
        if found:
            source_paths.append(file_found)

    data_headers = ('Table', 'Column', 'Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _epoch(value):
    if not isinstance(value, int) or value <= 0:
        return ''
    try:
        return (datetime(1970, 1, 1) + timedelta(seconds=value)).strftime('%Y-%m-%d %H:%M:%S')
    except OverflowError:
        return ''


@artifact_processor
def sdl_app_resumption(context):
    data_list = []
    source_paths = []
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found) or os.path.basename(file_found) != 'app_info.dat':
            continue
        relative = context.get_relative_path(file_found)
        try:
            with open(file_found, 'rb') as handle:
                resumption = json.loads(handle.read().decode('utf-8')).get('resumption')
        except (OSError, ValueError, AttributeError):
            logfunc(f'SDL application resumption: {relative} is not the JSON this reader '
                    'knows, not read')
            continue
        if not isinstance(resumption, dict):
            continue
        source_paths.append(file_found)
        last_off = resumption.get('last_ign_off_time')
        data_list.append((_epoch(last_off), 'Last ignition off', '', '', '', '', '',
                          _text(last_off), relative))
        for app in resumption.get('resume_app_list') or []:
            if not isinstance(app, dict):
                continue
            stamp = app.get('timeStamp')
            data_list.append((_epoch(stamp), 'Application', _text(app.get('appID')),
                              _text(app.get('deviceID')), _text(app.get('hmiLevel')),
                              _text(app.get('ign_off_count')),
                              _text(app.get('isMediaApplication')), _text(stamp), relative))

    data_headers = (('Time', 'datetime'), 'Row Kind', 'Application ID',
                    'Device ID (as stored)', 'HMI Level (as stored)',
                    'Ignition Off Count (as stored)', 'Media Application (as stored)',
                    'Time (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
