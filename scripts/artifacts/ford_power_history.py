__artifacts_v2__ = {
    "ford_power_history": {
        "name": "Power and Reset History",
        "description": "Reset detail blocks from the head unit's reset-history.txt, each "
                       "with its \"AP shutdown time\" and \"reset end time\" stamps, the boot "
                       "count, and the wake source and target mode stored in that block.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the Reset Details section of reset-history.txt. The file also opens "
                 "with a shorter summary table covering the same cycles; the detail blocks "
                 "are parsed instead because they carry more fields. Powered On is the "
                 "block's \"reset end time\" and Previous Shutdown is its \"AP shutdown time\"; "
                 "reading them as power on and shutdown rests on those field names. Neither "
                 "timestamp records a timezone. Both are stored as if they were UTC with no "
                 "offset applied, so they are clock readings and not established instants. Up "
                 "Time is the up-time figure on the \"reset end time\" line, shown as stored; "
                 "the header gives seconds and no source for that unit is cited here. Wake "
                 "source is reported as stored: on the tested image some values are words "
                 "(WakeupSource_Ignition, WakeupSource_DriverDoorAjar, "
                 "WakeupSource_PassengerDoorAjar, WakeupSource_DoorUnLocked, "
                 "WakeupSource_IlluminationActive) and others are bare numbers "
                 "(WakeupSource_23, _24, _27, _28, _29) that nothing available here "
                 "documents, so no meaning is assigned to them. A wake source names what the "
                 "unit recorded as waking it; it does not establish who was present or that "
                 "the vehicle moved. On the tested image the history did not hold every "
                 "cycle: it held 100 blocks covering boot counts 677 to 776, while "
                 "last-shutdown.txt in the same folder recorded boot count 777.",
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
        "notes": "From last-shutdown.txt, a file that held a single record on the tested "
                 "image. real time is read as a Unix time in milliseconds and divided by "
                 "1000. up-time and total up-time are reported as stored. On the tested "
                 "image this record sat one boot count ahead of the last block in "
                 "reset-history.txt, which shows the history file did not include the most "
                 "recent cycle.",
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
        "notes": "From reset-reason.txt, a file that held a single record on the tested "
                 "image. Same field vocabulary as last-shutdown.txt, and real time is read "
                 "the same way, as milliseconds divided by 1000. On the tested image this "
                 "record named a reset at a much lower boot count than the current one, so "
                 "the file does not necessarily describe the most recent power cycle. On the "
                 "tested image its timestamp fell 22 seconds before the first settings "
                 "write in the navigation application's own store, which is one observation. "
                 "Initiator and reason are reported as stored.",
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
                          uptime, total_uptime))

    data_headers = (('Powered On', 'datetime'), ('Previous Shutdown', 'datetime'),
                    'Boot Count', 'Wake Source (as stored)', 'Target Mode (as stored)',
                    'Reset Type', 'Reset Initiator', 'Reset Reason',
                    'Reboot Source (as stored)', 'Up Time (seconds)',
                    'Total Up Time (as stored)')
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


def _power_row(fields):
    """One row, shared by last-shutdown.txt and reset-reason.txt."""
    try:
        # The unit is known to be milliseconds, so it is divided here rather
        # than handed to a helper that infers the unit from magnitude.
        stamp = convert_unix_ts_to_utc(int(fields.get('real time', '')) / 1000)
    except ValueError:
        stamp = None
    return (stamp, fields.get('boot count', ''), fields.get('initiator', ''),
            fields.get('reason', ''), fields.get('up-time', ''),
            fields.get('total up-time', ''))


_POWER_HEADERS = (('Timestamp', 'datetime'), 'Boot Count', 'Initiator', 'Reason',
                  'Up Time (as stored)', 'Total Up Time (as stored)')


@artifact_processor
def ford_power_last_shutdown(context):
    fields, relative_path = _single_record(context, "last-shutdown.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields)], relative_path


@artifact_processor
def ford_power_reset_reason(context):
    fields, relative_path = _single_record(context, "reset-reason.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields)], relative_path
