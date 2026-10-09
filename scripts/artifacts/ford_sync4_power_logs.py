"""Ford SYNC 4: the stability monitor's reset history and event log.

The module's stability monitor keeps text files under fordlogs/sm:

    fordlogs/sm/reset-history.txt    a summary line and a detail block for each recent boot
    fordlogs/sm/smlog.<n>            the monitor's own log, one file per boot or more

A summary line is '<boot count> <date> <time> <reset type> <initiator> [<flag>]'. A detail
block is a run of 'name: value' lines that starts with 'boot count:'. A log line is
'<date> <time>[<seconds since boot>] <level> <text>'. None of the files records a time
zone.
"""

import os
import re
from datetime import datetime

from scripts.ilapfuncs import artifact_processor

__artifacts_v2__ = {
    "ford_sync4_reset_history": {
        "name": "Ford SYNC 4 - Reset History",
        "description": "One row for each boot in the stability monitor's reset history: when "
                       "the reset ended, when the previous shutdown was logged, the wake "
                       "source text, and the reset type, initiator and reason the file states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From fordlogs/sm/reset-history.txt, which holds a summary line and a detail "
                 "block for each recent boot; the two are merged on the boot count. Tested on "
                 "one Ford SYNC 4 unit read from its logical zip. The files record no time "
                 "zone, so times are the unit's clock readings, written out as if they were "
                 "UTC with no offset applied. It gave 100 rows, boot counts 677 to 776, with "
                 "reset end times from 2024-03-11 to 2024-03-29. Reset End Time is the detail "
                 "block's 'reset end time' and Previous Shutdown Time its 'AP shutdown time', "
                 "which the block attributes to the boot before. Wake Source is the text "
                 "inside WakeSource(...) of the block's RebootSourceData line, as stored: "
                 "eleven rows carry a name (passenger door ajar 4, illumination active 3, "
                 "ignition 2, door unlocked 1, driver door ajar 1) and 89 a number such as "
                 "WakeupSource_27, which nothing available here maps to a name. Reset type was "
                 "VMCU-normal on 99 rows and unknown on one, which also carries the summary "
                 "flag BootFailed; the reset reason was 'PwrMgr shutdown' on all 100. The "
                 "up-time columns are the seconds the lines state. The file is a window of "
                 "recent boots, not the unit's whole history. A row records what the module "
                 "logged about that boot. A wake source names the signal the module recorded, "
                 "not who caused it.",
        "paths": ('*/fordlogs/sm/reset-history.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 100 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_sync4_stability_events": {
        "name": "Ford SYNC 4 - Stability Monitor Events",
        "description": "Lines of the stability monitor's log: boot cycle starts, ignition and "
                       "power level changes, suspends, shutdowns, resets and faults, each with "
                       "its clock reading, seconds since boot and boot cycle.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From fordlogs/sm/smlog.<n>. Debug lines (level D), which are service "
                 "registrations and heartbeats, are left out; the other lines are reported. "
                 "Tested on one Ford SYNC 4 unit read from its logical zip. The files record "
                 "no time zone, so times are the unit's clock readings, written out as if they "
                 "were UTC with no offset applied. Fifteen files gave 1,602 rows covering 129 "
                 "boot cycles, 649 to 777, from 2024-03-01 to 2024-04-04. Event and Value are "
                 "the name and the first value in parentheses on the line, as stored, and "
                 "Number is the second value; Line Text keeps the whole line. Ignition lines "
                 "carried the values KeyOut (142), Run (97), IgnOff_DelayAccOn (66) and Crank "
                 "(12); power level lines Level1, Level2 and Level3. Nothing available here "
                 "documents those values, so none is relabelled. The 130 fault lines are 'Max "
                 "retry of shutdown requests has been exceeded' 129 times, once in each tested "
                 "boot cycle, and the same text for suspend once; what the fault means for the "
                 "unit is not established. Boot Cycle is the number in the 'stability monitor "
                 "started for boot cycle' line above the row. A row records that the module "
                 "logged that line. An ignition value does not establish who operated the "
                 "vehicle.",
        "paths": ('*/fordlogs/sm/smlog*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 1602 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
}

_SUMMARY = re.compile(r'^(\d+) (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+ (\S+)\s*\t([^\t]*)\t?(.*)$')
_DETAIL = re.compile(r'^([A-Za-z][A-Za-z ]*?):\s+(.*)$')
_DETAIL_TIME = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+ boot (\d+) up-time ([\d.]+)')
_WAKE = re.compile(r'WakeSource\(\s*([^)]*?)\s*\)')
_LOG = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d+\[(\d+\.\d+)\] ([A-Z]) (.*)$')
_EVENT = re.compile(r'^([a-z][a-z0-9-]*) \(([^,()]*)(?:,(-?\d+))?\)')
_BOOT = re.compile(r'^stability monitor started for boot cycle (\d+)')


def _files(context, prefix):
    return sorted(str(f) for f in set(context.get_files_found())
                  if not os.path.isdir(str(f)) and os.path.basename(str(f)).startswith(prefix))


def _lines(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return []


def _time(text):
    try:
        datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''
    return text


def _reset_history(lines):
    """Boot count -> merged values of that boot's summary line and detail block."""
    boots = {}
    block = None
    for line in lines:
        summary = _SUMMARY.match(line)
        if summary:
            boot = boots.setdefault(int(summary.group(1)), {})
            boot['summary time'] = summary.group(2)
            boot['summary type'] = summary.group(3)
            boot['summary initiator'] = summary.group(4).strip()
            boot['summary flag'] = summary.group(5).strip()
            continue
        detail = _DETAIL.match(line)
        if not detail:
            block = None if not line.strip() else block
            continue
        name, value = detail.group(1).strip(), detail.group(2).strip()
        if name == 'boot count' and value.isdigit():
            block = boots.setdefault(int(value), {})
        elif block is not None:
            block[name] = value
    return boots


@artifact_processor
def ford_sync4_reset_history(context):
    data_list = []
    source_paths = []
    for file_found in _files(context, 'reset-history.txt'):
        relative = context.get_relative_path(file_found)
        boots = _reset_history(_lines(file_found))
        if boots:
            source_paths.append(file_found)
        for count in sorted(boots, reverse=True):
            boot = boots[count]
            ended = _DETAIL_TIME.match(boot.get('reset end time', ''))
            shutdown = _DETAIL_TIME.match(boot.get('AP shutdown time', ''))
            wake = _WAKE.search(boot.get('RebootSourceData', ''))
            data_list.append((
                _time(ended.group(1) if ended else boot.get('summary time', '')),
                _time(shutdown.group(1)) if shutdown else '',
                count,
                wake.group(1) if wake else '',
                boot.get('reset type', boot.get('summary type', '')),
                boot.get('reset initiator', boot.get('summary initiator', '')),
                boot.get('reset reason', ''),
                boot.get('reboot source', ''),
                boot.get('PwrMgrPowerLevel', ''),
                ended.group(3) if ended else '',
                shutdown.group(3) if shutdown else '',
                boot.get('summary flag', ''),
                relative))

    data_headers = (('Reset End Time', 'datetime'), ('Previous Shutdown Time', 'datetime'),
                    'Boot Count', 'Wake Source (as stored)', 'Reset Type', 'Reset Initiator',
                    'Reset Reason', 'Reboot Source (as stored)',
                    'Power Level Text (as stored)', 'Up-Time At Reset End',
                    'Up-Time At Previous Shutdown', 'Summary Flag', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync4_stability_events(context):
    data_list = []
    source_paths = []
    for file_found in _files(context, 'smlog'):
        relative = context.get_relative_path(file_found)
        boot_cycle = ''
        found = False
        for number, line in enumerate(_lines(file_found), start=1):
            match = _LOG.match(line)
            if not match or match.group(3) == 'D':
                continue
            text = match.group(4)
            started = _BOOT.match(text)
            event = _EVENT.match(text)
            if started:
                boot_cycle = int(started.group(1))
                name, value, number_value = 'boot cycle started', str(boot_cycle), ''
            elif event:
                name, value, number_value = event.group(1), event.group(2), event.group(3) or ''
            else:
                name, value, number_value = '', '', ''
            found = True
            data_list.append((_time(match.group(1)), name, value, number_value, boot_cycle,
                              match.group(2), match.group(3), text, number, relative))
        if found:
            source_paths.append(file_found)

    data_headers = (('Log Time', 'datetime'), 'Event', 'Value (as stored)',
                    'Number (as stored)', 'Boot Cycle', 'Seconds Since Boot', 'Level',
                    'Line Text', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
