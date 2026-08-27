__artifacts_v2__ = {
    "ford_diag_events": {
        "name": "Diagnostic Events",
        "description": "Diagnostic events the head unit recorded, with the subsystem that "
                       "raised each one and the time it was uploaded where the record "
                       "carries one.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From events_metadata in diagnostics_slave.sqlite. The uploaded column is "
                 "declared INTEGER but holds a human readable date string once an event has "
                 "been uploaded and 0 before that, so both the parsed value and the string "
                 "as stored are reported. That string carries no timezone, so it is taken as "
                 "written with no conversion applied. On the tested image 180 of 424 rows "
                 "carried a date. create_time is NOT reported as a time: its values range "
                 "from 19 to 238080, it does not track uptime, and nothing available "
                 "establishes what it counts, so reporting it as a clock would be a guess. "
                 "event_type, event_severity and status are undocumented integers and are "
                 "reported as stored. creator_id names the subsystem; it is not an "
                 "indication of who was in the vehicle.",
        "paths": ('*/diagnostics/db/diagnostics_slave.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 424 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
    "ford_diag_upload_errors": {
        "name": "Diagnostic Upload Errors",
        "description": "Failures the head unit recorded while trying to upload diagnostic "
                       "events, each with a timestamp and the boot count current at the time.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From upload_errors in diagnostics_slave.sqlite. timestamp is a Unix time in "
                 "seconds. start_time is a separate human readable string with no timezone "
                 "and is reported as stored. boot_count is the unit's own counter and is "
                 "useful as a sequence: on the tested image 281 errors spanned boot counts "
                 "736 to 775 over six days, so the counter advances with power cycles, but "
                 "what exactly increments it is not established here. That range falls "
                 "inside the 677 to 776 window the unit's reset-history.txt records, so the "
                 "two stores can be read against each other. error_code is an "
                 "undocumented integer, reported as stored.",
        "paths": ('*/diagnostics/db/diagnostics_slave.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 281 rows",
        },
        "output_types": "standard",
        "artifact_icon": "alert-triangle",
    },
    "ford_diag_identifiers": {
        "name": "Diagnostic Identifiers",
        "description": "Identifier values the head unit stored beside its diagnostics "
                       "configuration, reported as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Each file holds a single 64 character hexadecimal value on one line, and "
                 "the file name is the unit's own name for it. A 64 character hex string is "
                 "the length a SHA-256 digest prints to, but what was hashed is not "
                 "established here: the VIN in the same folder was tested as a preimage in "
                 "several spellings and did not match any of the three, so no derivation is "
                 "asserted and the values are reported as stored. On the tested image the "
                 "three values were distinct from one another. The VIN itself is covered "
                 "separately by the artifact reading vin.txt, so these are an independent "
                 "identity record rather than a restatement of it.",
        "paths": ('*/diagnostics/*_id.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 3 rows",
        },
        "output_types": "standard",
        "artifact_icon": "hash",
    },
}

import re
from datetime import datetime, timezone

import os

from scripts.ilapfuncs import (artifact_processor, convert_unix_ts_to_utc,
                               get_file_path, logdevinfo,
                               open_sqlite_db_readonly)


def _parse_ctime_string(value):
    """A 'Wed Nov 29 06:41:41 2023' style string, or None.

    The device writes no timezone, so the value is taken as written rather than
    shifted. Single digit days are padded with a second space, which strptime
    will not accept, so runs of whitespace are collapsed first.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(re.sub(r'\s+', ' ', value.strip()),
                                 '%a %b %d %H:%M:%S %Y').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@artifact_processor
def ford_diag_events(context):
    data_list = []
    source_path = get_file_path(context.get_files_found(), "diagnostics_slave.sqlite")
    if not source_path:
        return (), [], ''
    db = open_sqlite_db_readonly(source_path)
    if db is None:
        return (), [], context.get_relative_path(source_path)
    cursor = db.cursor()
    cursor.execute('''
        SELECT uploaded, creator_id, ecu, event_type, event_severity,
               status, uptime, create_time, geid
        FROM events_metadata
        ORDER BY uptime
    ''')
    for row in cursor.fetchall():
        uploaded = row[0]
        parsed = _parse_ctime_string(uploaded)
        as_stored = uploaded if isinstance(uploaded, str) else ''
        data_list.append((parsed, as_stored, row[1], row[2], row[3], row[4],
                          row[5], row[6], row[7], row[8],
                          context.get_relative_path(source_path)))
    db.close()

    data_headers = (('Uploaded', 'datetime'), 'Uploaded (as stored)', 'Creator',
                    'ECU', 'Event Type (as stored)', 'Severity (as stored)',
                    'Status (as stored)', 'Uptime (as stored)',
                    'create_time (as stored)', 'Event ID', 'Source File')
    return data_headers, data_list, context.get_relative_path(source_path)


@artifact_processor
def ford_diag_upload_errors(context):
    data_list = []
    source_path = get_file_path(context.get_files_found(), "diagnostics_slave.sqlite")
    if not source_path:
        return (), [], ''
    db = open_sqlite_db_readonly(source_path)
    if db is None:
        return (), [], context.get_relative_path(source_path)
    cursor = db.cursor()
    cursor.execute('''
        SELECT timestamp, start_time, boot_count, error_code, error_text,
               duration_sec, transmitter_id, wakelock, event_id
        FROM upload_errors
        ORDER BY timestamp
    ''')
    for row in cursor.fetchall():
        data_list.append((convert_unix_ts_to_utc(row[0]), row[1], row[2], row[3],
                          row[4], row[5], row[6], row[7], row[8],
                          context.get_relative_path(source_path)))
    db.close()

    data_headers = (('Timestamp', 'datetime'), 'Start Time (as stored)', 'Boot Count',
                    'Error Code (as stored)', 'Error Text', 'Duration (seconds)',
                    'Transmitter', 'Wakelock', 'Event ID', 'Source File')
    return data_headers, data_list, context.get_relative_path(source_path)


@artifact_processor
def ford_diag_identifiers(context):
    data_list = []
    source_paths = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'r', encoding='utf-8', errors='replace') as handle:
                value = handle.read(4096).strip()
        except OSError:
            continue
        if not value:
            continue
        key = os.path.basename(file_found)
        source_paths.append(file_found)
        data_list.append((key, value, len(value),
                          context.get_relative_path(file_found)))
        logdevinfo(f"Ford diagnostic identifier {key}: {value}")

    data_headers = ('File', 'Stored Value', 'Length', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
