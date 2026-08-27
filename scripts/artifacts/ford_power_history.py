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
}

import re
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, get_file_path

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
