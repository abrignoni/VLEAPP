"""System manager logs kept by QNX head units of more than one make.

Named for the log, not a vehicle: the same two files, in the same line format, are kept
under a logs folder by the Ford SYNC Gen3 module and by the GM GA-130 radio.

    logs/sys_error.log.<n>      the system manager's event log
    logs/sys_cpu_usage[.<n>]    CPU usage samples, in blocks headed by a boot count

A line of either file starts with a clock reading, <MM/DD/YYYY hh:mm:ss.mmm>/. The files
record no time zone. A reading with the year 1970 was written before the unit's clock was
set, so it is an uptime and not a date.
"""

import os
import re
from datetime import datetime

from scripts.ilapfuncs import artifact_processor

__artifacts_v2__ = {
    "system_manager_log_events": {
        "name": "System Manager Log - Events",
        "description": "Lines of the system manager's event log: boot cycles, wake-ups, "
                       "suspends, shutdowns and process failures, each with its clock reading "
                       "and the boot cycle number of the nearest boot line above it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "System Manager Logs",
        "notes": "From logs/sys_error.log.<n>. The same file and line format are kept by the "
                 "Ford SYNC Gen3 module and the GM GA-130 radio, so the artifact is named for "
                 "the log. Tested on three units: a 2018 Ford Expedition (SYNC Gen3), read "
                 "from its export, a 2014 Chevrolet Equinox LT and a 2015 Chevrolet Malibu "
                 "(GA-130), read from their extracted file sets. They gave 6,680, 6,027 and "
                 "4,985 rows. A line starts with a clock reading in angle brackets, month "
                 "first. The files record no time zone, so the time is the unit's clock "
                 "reading, written out as if it were UTC with no offset applied. A reading "
                 "with the year 1970 was written before the unit's clock was set; it is an "
                 "uptime and not a date, so its time column is left empty and the reading is "
                 "still shown as stored. On the Ford unit 594 rows have a 1970 reading and the "
                 "rest run from 2014 to 2026; on the GM units 5,041 and 4,127 rows have one. "
                 "Boot Cycle Above is the number in the nearest 'New Boot Cycle = <n>' line "
                 "above the row in the same file; the Ford unit numbers its boots (767 to "
                 "1,822 in the two files) and the GM units write the line without a number, so "
                 "the column is empty there. On the Ford unit 565 of 1,044 boot lines carry a "
                 "date; on the GM units no boot line does. The Ford log has 18 distinct line "
                 "texts and the GM logs 43 and 52, most of them internal status lines; every "
                 "line is reported so the sequence around an event can be read. A row records "
                 "that the unit logged that line at that clock reading. What caused a shutdown "
                 "or a wake-up is not established.",
        "paths": ('*/logs/sys_error.log*',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | "
                                       "6680 rows",
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 6027 rows",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 4985 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "system_manager_log_powered_sessions": {
        "name": "System Manager Log - CPU Sample Sessions",
        "description": "One row for each block of CPU usage samples in the usage log, with the "
                       "boot count the block is headed by, the clock readings of its first and "
                       "last sample and the number of samples.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "System Manager Logs",
        "notes": "From logs/sys_cpu_usage and sys_cpu_usage.<n>. The file is written in "
                 "blocks: a 'BOOT COUNT = <n>' line, then one 'CPU <n> Usage' line per core "
                 "about every 30 seconds while the unit runs. The samples themselves are load "
                 "figures and are not listed; each block is folded into one row, and a block "
                 "with no sample gives no row. Tested on one unit, a 2018 Ford Expedition "
                 "(SYNC Gen3), read from its export: 1,513 blocks, 1,409 of them with samples, "
                 "111,366 samples in all, boot counts 18 to 1,822. The two tested GM GA-130 "
                 "units have no such file. A line starts with a clock reading in angle "
                 "brackets, month first. The files record no time zone, so the time is the "
                 "unit's clock reading, written out as if it were UTC with no offset applied. "
                 "A reading with the year 1970 was written before the unit's clock was set; it "
                 "is an uptime and not a date, so its time column is left empty and the "
                 "reading is still shown as stored. No tested sample had a 1970 reading; first "
                 "samples fall in 2018 to 2026 on all but five blocks, which read 2000 or 2014 "
                 "and so were written with the clock unset or wrong. In five blocks the last "
                 "reading is earlier than the first, which means the clock was changed inside "
                 "the block. The first and last samples bound the time the unit was running "
                 "and logging in that boot. They do not establish that the vehicle was driven.",
        "paths": ('*/logs/sys_cpu_usage*',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "2018 Ford Expedition, SYNC Gen3, Berla iVe export | "
                                       "1409 rows",
            "xtrmp_item025": "2014 Chevy Equinox LT, GA-130, extracted file set | 0 rows, no "
                             "sys_cpu_usage file in the extracted set",
            "xtrmp_item061": "2015 Chevrolet Malibu, GA-130, extracted file set | 0 rows, no "
                             "sys_cpu_usage file in the extracted set",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
}

_LINE = re.compile(r'^<(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)>/(.*)$')
_BOOT_CYCLE = re.compile(r'^New Boot Cycle = (\d+)')
_BOOT_COUNT = re.compile(r'BOOT COUNT = (\d+)')
_CPU_SAMPLE = re.compile(r'^\s*CPU \d+ Usage')


def _files(context, prefix):
    return sorted(str(f) for f in set(context.get_files_found())
                  if not os.path.isdir(str(f)) and os.path.basename(str(f)).startswith(prefix))


def _lines(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return []


def _clock(match):
    """(log time or '', the reading as stored). The time is empty for a 1970 reading."""
    month, day, year, hour, minute, second = (int(value) for value in match.groups()[:6])
    stored = (f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'
              f'.{match.group(7)}')
    if year == 1970:
        return '', stored
    try:
        stamp = datetime(year, month, day, hour, minute, second)
    except ValueError:
        return '', stored
    return stamp.strftime('%Y-%m-%d %H:%M:%S'), stored


@artifact_processor
def system_manager_log_events(context):
    data_list = []
    source_paths = []
    for file_found in _files(context, 'sys_error.log'):
        relative = context.get_relative_path(file_found)
        boot_cycle = ''
        found = False
        for number, line in enumerate(_lines(file_found), start=1):
            match = _LINE.match(line)
            if not match:
                continue
            text = match.group(8).strip()
            cycle = _BOOT_CYCLE.match(text)
            if cycle:
                boot_cycle = int(cycle.group(1))
            stamp, stored = _clock(match)
            found = True
            data_list.append((stamp, stored, text, boot_cycle, number, relative))
        if found:
            source_paths.append(file_found)

    data_headers = (('Log Time', 'datetime'), 'Clock Reading (as stored)', 'Event',
                    'Boot Cycle Above', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def system_manager_log_powered_sessions(context):
    data_list = []
    source_paths = []
    for file_found in _files(context, 'sys_cpu_usage'):
        relative = context.get_relative_path(file_found)
        sessions = []
        current = None
        for number, line in enumerate(_lines(file_found), start=1):
            boot = _BOOT_COUNT.search(line)
            if boot and not _LINE.match(line):
                current = [int(boot.group(1)), '', '', '', '', 0, number]
                sessions.append(current)
                continue
            match = _LINE.match(line)
            if not match or current is None or not _CPU_SAMPLE.match(match.group(8)):
                continue
            stamp, stored = _clock(match)
            if not current[5]:
                current[1], current[3] = stamp, stored
            current[2], current[4] = stamp, stored
            current[5] += 1
        rows = [tuple(session) + (relative,) for session in sessions if session[5]]
        if rows:
            source_paths.append(file_found)
        # first sample time, last sample time, boot count, readings as stored, samples, line
        data_list.extend((row[1], row[2], row[0], row[3], row[4], row[5], row[6], row[7])
                         for row in rows)

    data_headers = (('First Sample Time', 'datetime'), ('Last Sample Time', 'datetime'),
                    'Boot Count', 'First Reading (as stored)', 'Last Reading (as stored)',
                    'Samples', 'Block Starts At Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
