"""Ford SYNC on Windows CE: vehicle and device events in the module's debug log.

The module writes a rolling text log, Windows/LogFiles/MsgLog<n>.txt. Among its lines are
door, gear position, ignition, odometer, USB attach and phone connection lines. Each line
starts with a tick count and none carries a date; the log's only wall clock is in its
'start saving retailmsg' lines.

The same lines survive in the raw partition image an acquisition carries, in blocks the
file system has released, so this module reads both:

    Windows/LogFiles/MsgLog<n>.txt      the live log files
    DiskImages/partition<n>.img         the raw partition, read as bytes

In an image no file system is followed. An event line is found by its own text, and the
lines around it are used only when the bytes between them are all log text, so a clock
is never carried across a break in the log.
"""

import mmap
import os
import re
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "ford_sync_wince_log_events": {
        "name": "Ford SYNC WinCE - Log Events",
        "description": "Door, gear position, ignition, odometer, USB attach and phone "
                       "connection lines from the module's debug log, read from the log files "
                       "and from the raw partition image, each with its tick count and a clock "
                       "derived from the nearest log save line.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt and from DiskImages/partition<n>.img, "
                 "the raw partition an acquisition carries, which is read as bytes with no "
                 "file system followed. Tested on ten units from their acquisition folders: "
                 "eight SYNC Gen1 (Ford Escape 2010 to 2014, Edge 2013, Fusion 2019) and two "
                 "SYNC Gen2 (2014 Ford Edge SEL, 2011 Ford Explorer XLT). They gave 1,901 rows "
                 "in all, 1,692 of them on the two Gen2 units; one Gen2 unit had no log file "
                 "in its extracted set and gave 652 rows from its partition image alone. The "
                 "image holds log blocks the file system has released, so it gives more than "
                 "the files: on the 2014 Edge 47 event lines were in the files and 1,047 in "
                 "the image. A line found in more than one place is reported once, with Times "
                 "Found. Which lines exist depends on the generation: door, gear, ignition and "
                 "USB lines came only from Gen2, phone lines only from the Gen1 version 5 "
                 "unit, and odometer lines from both. No line carries a date. Derived Clock is "
                 "the clock in the nearest 'start saving retailmsg' line plus the difference "
                 "in ticks read as milliseconds, and it is filled only when that line and the "
                 "event stand in one unbroken stretch of log text with ticks that never go "
                 "down. Nearest Save Clock and Seconds From Save Line show what it was derived "
                 "from; the further the event is from the save line, the more a clock change "
                 "in between can put it off, and distances up to a few hours occur. The tick "
                 "unit was checked on the log files: of 78 pairs of save lines in one stretch, "
                 "35 agreed with milliseconds to within two seconds and the others span a "
                 "change of the clock. 1,120 of the 1,901 rows have no save line in their "
                 "stretch and no derived clock. The derived clock was compared with an "
                 "independent parse of the 2014 Edge: of 94 door events with a clock, 44 "
                 "matched a door event of the same kind within two seconds, and 47 of the "
                 "other 50 stand in stretches of log that parse does not list at all. The "
                 "clock is the module's own and can be unset; readings in 2003 and 2010 occur. "
                 "Value is the number on the line as stored: the gear position value, the "
                 "ignition state value, the USB port, or the odometer reading. Nothing "
                 "available here documents the gear and ignition values, and the same gear "
                 "value was labelled differently by that independent parse at different times, "
                 "so no label is given. The Gen1 odometer line carries two numbers, shown as "
                 "Value and Second Value; the Gen2 line carries one. The log repeats the "
                 "odometer reading, so it is reported when it changes within a stretch. For "
                 "phone lines Detail is the device name and Value is the address on the line. "
                 "A row records that the module logged that line. It does not establish who "
                 "opened a door or drove the vehicle. Not read: the raw NAND image "
                 "(LargeOutputFiles/image.nbo), which interleaves spare bytes with the data.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/DiskImages/partition*.img'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 0 rows, no "
                             "event line in the log files or the partition image",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 7 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 8 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 12 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 22 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 50 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 1040 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 652 rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 74 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 36 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
}

_EVENT = re.compile(
    rb'(?P<tick>\d{1,10}) +(?:'
    rb'(?P<door>(?:-->|<--) (?:Driver|Passenger) door was (?:opened|closed))'
    rb'|AppConsole: GEARPOS event received, Value = (?P<gear>\d+)'
    rb'|CVHR:GetOdometerReading--: SUCCESS ODOMETER = (?P<odo2>\d+)'
    rb'|CVhrDiagControl::GetOdometerReading\(\)\s+ODO = (?P<odo1>\d+) \((?P<odo1b>\d+)\)'
    rb'|TDIHandler::HandleIgnitionStateChange\((?P<ignition>\d+)\)'
    rb'|CHub::HubStatusChangeThread - device attached on port (?P<usb>\d+)'
    rb"|APP-PHONE-(?P<phone>CONNECT: Current|DISCONNECT: Last) device: '(?P<name>[^\r\n]{0,80}?)'"
    rb' \(0x(?P<address>[0-9A-Fa-f]+)\)'
    rb'|SYSHEALTH: start saving retailmsg at (?P<save>\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)'
    rb')')
_NOT_LOG_TEXT = re.compile(rb'[^\t\r\n\x20-\x7e]')


def _sources(context):
    """Matched files as (path, bytes-like, close), mapping images instead of reading them."""
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        try:
            if os.path.getsize(file_found) == 0:
                continue
            handle = open(file_found, 'rb')  # pylint: disable=consider-using-with
        except OSError:
            continue
        try:
            mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        except (OSError, ValueError):
            handle.close()
            continue
        try:
            yield file_found, mapped
        finally:
            mapped.close()
            handle.close()


def _address(text):
    digits = text.rjust(12, '0')[-12:].lower()
    return ':'.join(digits[i:i + 2] for i in range(0, 12, 2))


def _describe(match):
    """(event, detail, value, second value) for a matched event line; None for a save line."""
    if match.group('door'):
        return 'Door', match.group('door').decode('latin-1')[4:], '', ''
    if match.group('gear'):
        return 'Gear Position', '', int(match.group('gear')), ''
    if match.group('odo2'):
        return 'Odometer', '', int(match.group('odo2')), ''
    if match.group('odo1'):
        return 'Odometer', '', int(match.group('odo1')), int(match.group('odo1b'))
    if match.group('ignition'):
        return 'Ignition State Change', '', int(match.group('ignition')), ''
    if match.group('usb'):
        return 'USB Device Attached', '', int(match.group('usb')), ''
    if match.group('phone'):
        event = 'Phone Connect' if match.group('phone').startswith(b'CONNECT') \
            else 'Phone Disconnect'
        return (event, match.group('name').decode('utf-8', 'replace'),
                _address(match.group('address').decode('ascii')), '')
    return None


def _save_clock(match):
    try:
        return datetime.strptime(match.group('save').decode('ascii'), '%m/%d/%Y %H:%M:%S')
    except ValueError:
        return None


def _sessions(data):
    """Runs of matched lines that share one stretch of log and one boot.

    Two matched lines belong together only when every byte between them is log text and
    the tick count has not gone down, which is what a restart or an unrelated block
    looks like. Each run is a list of regex matches in written order.
    """
    run = []
    previous_end = None
    previous_tick = None
    for match in _EVENT.finditer(data):
        tick = int(match.group('tick'))
        joined = previous_end is not None and tick >= previous_tick and \
            _NOT_LOG_TEXT.search(data, previous_end, match.start()) is None
        if not joined and run:
            yield run
            run = []
        run.append(match)
        previous_end = match.end()
        previous_tick = tick
    if run:
        yield run


def _nearest(anchors, tick):
    """The (tick, clock) save line closest in ticks to an event."""
    best = anchors[0]
    for anchor in anchors[1:]:
        if abs(anchor[0] - tick) < abs(best[0] - tick):
            best = anchor
    return best


def _events(data):
    """Event rows of one source, each with the clock derived from the nearest save line."""
    for run in _sessions(data):
        anchors = [(int(m.group('tick')), _save_clock(m)) for m in run if m.group('save')]
        anchors = [anchor for anchor in anchors if anchor[1] is not None]
        last_odometer = None
        for match in run:
            described = _describe(match)
            if described is None:
                continue
            tick = int(match.group('tick'))
            if described[0] == 'Odometer':
                # The log repeats the reading; keep it when it changes.
                if described[2:] == last_odometer:
                    continue
                last_odometer = described[2:]
            derived = anchor_clock = ''
            seconds = ''
            if anchors:
                anchor_tick, clock = _nearest(anchors, tick)
                seconds = round((tick - anchor_tick) / 1000.0, 1)
                derived = (clock + timedelta(milliseconds=tick - anchor_tick)).strftime(
                    '%Y-%m-%d %H:%M:%S')
                anchor_clock = clock.strftime('%Y-%m-%d %H:%M:%S')
            yield (derived,) + described + (tick, anchor_clock, seconds), match.start()


@artifact_processor
def ford_sync_wince_log_events(context):
    rows = {}
    source_paths = []
    for file_found, data in _sources(context):
        found = 0
        for row, offset in _events(data):
            found += 1
            if row in rows:
                rows[row][0] += 1
            else:
                rows[row] = [1, offset, file_found]
                if file_found not in source_paths:
                    source_paths.append(file_found)
        logfunc(f'Ford SYNC WinCE log events: {found} event lines in '
                f'{os.path.basename(file_found)}')
    data_list = [row + (found, offset, context.get_relative_path(path))
                 for row, (found, offset, path) in rows.items()]
    data_list.sort(key=lambda row: (row[0] == '', row[0], row[5]))

    data_headers = (('Derived Clock', 'datetime'), 'Event', 'Detail', 'Value (as stored)',
                    'Second Value (as stored)', 'Tick', ('Nearest Save Clock', 'datetime'),
                    'Seconds From Save Line', 'Times Found', 'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
