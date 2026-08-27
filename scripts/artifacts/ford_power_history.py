__artifacts_v2__ = {
    "ford_power_history": {
        "name": "Power and Reset History",
        "description": "Power cycles the head unit recorded, each with the time it shut "
                       "down, the time it came back up, the boot count, and the wake source "
                       "and target mode the unit stored for that cycle.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the Reset Details section of reset-history.txt. The file also opens "
                 "with a shorter summary table covering the same cycles; the detail blocks "
                 "are parsed instead because they carry more fields. Neither timestamp "
                 "records a timezone, so both are taken as written with no conversion "
                 "applied. Wake source is reported as stored: on the tested image some "
                 "values are words (WakeupSource_Ignition, WakeupSource_DriverDoorAjar, "
                 "WakeupSource_PassengerDoorAjar, WakeupSource_DoorUnLocked, "
                 "WakeupSource_IlluminationActive) and others are bare numbers "
                 "(WakeupSource_23, _24, _27, _28, _29) that nothing available here "
                 "documents, so no meaning is assigned to them. A wake source names what the "
                 "unit recorded as waking it; it does not establish who was present or that "
                 "the vehicle moved. The history is a fixed window rather than a complete "
                 "record: the tested image held exactly 100 blocks covering boot counts 677 "
                 "to 776, while last-shutdown.txt in the same folder recorded boot count 777, "
                 "so older cycles had already aged out.",
        "paths": ('*/fordlogs/sm/reset-history.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 100 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_power_last_shutdown": {
        "name": "Last Shutdown",
        "description": "The shutdown the head unit recorded most recently, with the boot "
                       "count, the time, the uptime for that cycle and the initiator and "
                       "reason it stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From last-shutdown.txt, a single record that the unit overwrites, so it "
                 "reflects one cycle rather than a history. real time is a Unix time in "
                 "milliseconds and is divided at the call site because the unit is known "
                 "rather than inferred from magnitude. up-time and total up-time are "
                 "reported as stored. On the tested image this record sat one cycle ahead of "
                 "the window in reset-history.txt, which is what shows that history is "
                 "capped rather than complete.",
        "paths": ('*/fordlogs/sm/last-shutdown.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_power_reset_reason": {
        "name": "Last Reset Reason",
        "description": "The reset the head unit recorded most recently in its own reset "
                       "reason file, with the boot count, the time, and the initiator and "
                       "reason it stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From reset-reason.txt, a single record the unit overwrites. Same field "
                 "vocabulary as last-shutdown.txt and the same millisecond epoch, divided at "
                 "the call site. On the tested image this record named a reset at a much "
                 "lower boot count than the current one, so the file does not necessarily "
                 "describe the most recent power cycle. On the tested image its timestamp "
                 "fell 22 seconds before the first settings write in the navigation "
                 "application's own store, which is independent corroboration of the same "
                 "event. Initiator and reason are reported as stored.",
        "paths": ('*/fordlogs/sm/reset-reason.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "rotate-ccw",
    },
}

import re
from datetime import datetime, timezone

from scripts.ilapfuncs import (artifact_processor, convert_unix_ts_to_utc,
                               get_file_path)

# "2024-03-29 10:11:53.257 boot 776 up-time 073.676 total-up-time 678157"
_STAMP = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)'
                    r'(?:\s+boot \d+ up-time ([\d.]+) total-up-time (\d+))?')
_FIELD = re.compile(r'^\s*([A-Za-z][A-Za-z /]*?):\s{2,}(.*?)\s*$')


def _parse_stamp(value):
    """The datetime from a stamped line, or None.

    The device writes no timezone, so the value is taken as written rather
    than shifted.
    """
    match = _STAMP.search(value or '')
    if not match:
        return None, '', ''
    try:
        parsed = datetime.strptime(match.group(1),
                                   '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
    except ValueError:
        return None, '', ''
    return parsed, match.group(2) or '', match.group(3) or ''


@artifact_processor
def ford_power_history(context):
    data_list = []
    source_path = get_file_path(context.get_files_found(), "reset-history.txt")
    if not source_path:
        return (), [], ''
    try:
        with open(source_path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    except OSError:
        return (), [], context.get_relative_path(source_path)

    # The summary table comes first, then the per-cycle detail blocks.
    _, _, details = text.partition('Reset Details')
    for block in re.split(r'\n(?=boot count:)', details):
        if not block.strip().startswith('boot count:'):
            continue
        fields = {}
        for line in block.splitlines():
            match = _FIELD.match(line)
            if match:
                fields[match.group(1).strip()] = match.group(2)

        came_up, uptime, total_uptime = _parse_stamp(fields.get('reset end time', ''))
        went_down, _, _ = _parse_stamp(fields.get('AP shutdown time', ''))

        wake = re.search(r'WakeSource\(([^)]*)\)', fields.get('RebootSourceData', ''))
        mode = re.search(r'TargetMode_(\w+)', fields.get('PwrMgrPowerLevel', ''))

        data_list.append((came_up, went_down, fields.get('boot count', ''),
                          wake.group(1).strip() if wake else '',
                          mode.group(1) if mode else '',
                          fields.get('reset type', ''), fields.get('reset initiator', ''),
                          fields.get('reset reason', ''), fields.get('reboot source', ''),
                          uptime, total_uptime,
                          context.get_relative_path(source_path)))

    data_headers = (('Powered On', 'datetime'), ('Previous Shutdown', 'datetime'),
                    'Boot Count', 'Wake Source (as stored)', 'Target Mode (as stored)',
                    'Reset Type', 'Reset Initiator', 'Reset Reason',
                    'Reboot Source (as stored)', 'Up Time (seconds)',
                    'Total Up Time (as stored)', 'Source File')
    return data_headers, data_list, context.get_relative_path(source_path)


def _single_record(context, filename):
    """The one key/value record these single-cycle files hold, or None."""
    source_path = get_file_path(context.get_files_found(), filename)
    if not source_path:
        return None, ''
    try:
        with open(source_path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    except OSError:
        return None, context.get_relative_path(source_path)
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(':')
        if sep:
            fields[key.strip()] = value.strip()
    return fields, context.get_relative_path(source_path)


def _power_row(fields, relative_path):
    """One row, shared by last-shutdown.txt and reset-reason.txt."""
    try:
        # The unit is known to be milliseconds, so it is divided here rather
        # than handed to a helper that infers the unit from magnitude.
        stamp = convert_unix_ts_to_utc(int(fields.get('real time', '')) / 1000)
    except ValueError:
        stamp = None
    return (stamp, fields.get('boot count', ''), fields.get('initiator', ''),
            fields.get('reason', ''), fields.get('up-time', ''),
            fields.get('total up-time', ''), relative_path)


_POWER_HEADERS = (('Timestamp', 'datetime'), 'Boot Count', 'Initiator', 'Reason',
                  'Up Time (as stored)', 'Total Up Time (as stored)', 'Source File')


@artifact_processor
def ford_power_last_shutdown(context):
    fields, relative_path = _single_record(context, "last-shutdown.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields, relative_path)], relative_path


@artifact_processor
def ford_power_reset_reason(context):
    fields, relative_path = _single_record(context, "reset-reason.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields, relative_path)], relative_path
