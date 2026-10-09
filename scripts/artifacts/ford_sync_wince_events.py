"""Ford SYNC on Windows CE: vehicle and device events in the module's debug log.

The module writes a rolling text log, Windows/LogFiles/MsgLog<n>.txt. Among its lines are
door, gear position, park lamp, ignition, odometer, USB attach and phone connection lines.
Each line starts with a tick count and none carries a date. Two other lines state a
date and time: the 'start saving retailmsg' line and, on generation 2, the clock service
line.

The same lines survive in the raw partition image an acquisition carries, in blocks the
file system has released, so this module reads both:

    Windows/LogFiles/MsgLog<n>.txt      the live log files
    Windows/DumpFiles/<dump>/<dump>.RTL the log text saved beside a crash dump
    DiskImages/partition<n>.img         the raw partition, read as bytes
    LargeOutputFiles/image.nbo          the raw NAND image, read for call list documents

In an image no file system is followed to find a hit. An event line is found by its own
text, and the lines around it are used only when the bytes between them are all log text,
so a clock is never carried across a break in the log. Call list documents are found the
same way in an exFAT partition image.

For an exFAT partition image the vendored reader is then asked two things, to say where
each hit sits: which clusters the allocation bitmap has clear, and what the files the
directory tree lists contain.
"""

import bisect
import mmap
import os
import re
import struct
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc
from scripts.raw_image import qnxprobe

__artifacts_v2__ = {
    "ford_sync_wince_log_events": {
        "name": "Ford SYNC WinCE - Log Events",
        "description": "Door, gear position, park lamp, ignition, odometer, reboot source, USB "
                       "attach and phone connection lines from the module's debug log, read "
                       "from the log files and from the raw partition image, each with its "
                       "tick count, a clock derived from the nearest line that states a "
                       "date and time, and where in the image it was found.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.4",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt and from DiskImages/partition<n>.img, "
                 "the raw partition an acquisition carries, which is read as bytes with no "
                 "file system followed. Tested on ten units from their acquisition folders: "
                 "eight SYNC Gen1 (Ford Escape 2010 to 2014, Edge 2013, Fusion 2019) and two "
                 "SYNC Gen2 (2014 Ford Edge SEL, 2011 Ford Explorer XLT). They gave 2,439 rows "
                 "in all, 2,230 of them on the two Gen2 units; one Gen2 unit had no log file "
                 "in its extracted set and gave 886 rows from its partition image alone. The "
                 "image holds log blocks the file system has released, so it gives more than "
                 "the files. The log text saved beside a crash dump, "
                 "Windows/DumpFiles/<dump>/<dump>.RTL, is read too; on the tested acquisition "
                 "folders every event line in it was also found in the partition image, so it "
                 "added no row there, and from the extracted file set alone it added 41 rows "
                 "on three units. A line found in more than one place is reported once, with "
                 "Times Found. Which lines exist depends on the generation: door, gear, park "
                 "lamp, ignition, reboot and USB lines came only from Gen2, phone lines only "
                 "from the Gen1 version 5 unit, and odometer lines from both. No event line "
                 "carries a date. Two other lines do: the log save line ('start saving "
                 "retailmsg at', written month first) and, on Gen2, the clock service line "
                 "('SyncClockSvc!MFDMessageThreadProc: (YMDhms)', written year first, about "
                 "once a minute). Derived Clock is the clock of the nearest such line plus the "
                 "difference in ticks read as milliseconds, and it is filled only when that "
                 "line and the event stand in one unbroken stretch of log text with ticks that "
                 "never go down. Nearest Clock Line, Clock Line Kind and Seconds From Clock "
                 "Line show what it was derived from; the further apart, the more a clock "
                 "change in between can put it off. 1,520 of the 2,439 rows have a derived "
                 "clock. The reading of ticks as milliseconds was checked: on the 2014 Edge "
                 "all 76 pairs of consecutive clock service lines in one stretch agreed with "
                 "it to within two seconds, and in the four places where a save line and a "
                 "clock service line stood together they gave the same clock to within five "
                 "seconds. Across the log files, 35 of 78 pairs of save lines agreed with it "
                 "and the others span a change of the clock. The derived clock was compared "
                 "with an independent parse of the 2014 Edge: of 167 door events with a clock, "
                 "100 matched a door event of the same kind within two seconds. The other 67 "
                 "have no counterpart in it within two seconds, and why was not resolved. The "
                 "clock is the module's own and can be unset; readings in 2003 and 2010 occur. "
                 "Clock Bias Minutes is the Bias value of the nearest clock service bias line "
                 "in the same stretch, as stored; the log states it as time zone plus user "
                 "offset, 300 and 360 occurred on the 2014 Edge, and it is empty where the "
                 "stretch has no such line. It is not applied to the clock. Value is the "
                 "number on the line as stored: the gear position, park lamp status, ignition "
                 "state, USB port, reboot source code or odometer reading. Nothing available "
                 "here documents the gear, ignition or reboot values, and that independent "
                 "parse labelled the same gear value differently at different times, so no "
                 "label is given. Where a park lamp line matched one of its events by time, "
                 "status 0 was labelled off 32 times and status 1 on 28 times and off 4 times; "
                 "the value is left as stored. The Gen1 odometer line carries two numbers, "
                 "shown as Value and Second Value; the Gen2 line carries one. The log repeats "
                 "the odometer reading, so it is reported when it changes within a stretch. "
                 "For phone lines Detail is the device name and Value is the address on the "
                 "line. Where Found says where the lines of a row sit, and lists every place "
                 "when a row was found more than once. A row from a log file of the extracted "
                 "set reads 'extracted file'. For an exFAT partition image the vendored reader "
                 "reads the allocation bitmap and the files the directory tree lists: 'free "
                 "cluster' is a cluster the bitmap has clear, 'in a listed file' an allocated "
                 "cluster whose line text a listed file also holds, and 'allocated cluster, in "
                 "no listed file' an allocated cluster whose line text no listed file holds. "
                 "The last two are decided by comparing text, not by following each file's "
                 "clusters. On the 2014 Edge 935 rows sat only in free clusters, 356 only in "
                 "allocated clusters in no listed file and 52 in a listed file; on the 2011 "
                 "Explorer 513 and 373, with no listed file holding any. Why those clusters "
                 "are allocated is not established. The eight Gen1 partition images are FAT "
                 "with 2,048-byte sectors, which the reader does not read, and their rows read "
                 "'file system not read'. A row records that the module logged that line. It "
                 "does not establish who opened a door or drove the vehicle.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 0 rows, no "
                             "event line in the log files or the partition image",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 7 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 8 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 12 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 22 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 50 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 1344 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 886 rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 74 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 36 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
    "ford_sync_wince_flash_call_history": {
        "name": "Ford SYNC WinCE - Call History In Flash Image",
        "description": "Call list entries read from the call list documents in the module's "
                       "raw NAND image, with the list, name, number and call time of each "
                       "entry and how many documents in the image hold it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From LargeOutputFiles/image.nbo, the raw NAND image an acquisition carries, "
                 "matched inside an acquisition folder or given on its own with the "
                 "single-file input type. The image stores each 2,048-byte page followed by 64 "
                 "spare bytes; the spare bytes are dropped and the result is searched for "
                 "complete call list documents, the same <Device> XML the module keeps as "
                 "Windows/phonebook/CH<address>.xml. No file system is followed, and only a "
                 "document complete from its opening to its closing tag is read. Tested on the "
                 "images of eight SYNC Gen1 units (Ford Escape 2010 to 2014, Edge 2013, Fusion "
                 "2019). The page layout is checked by the data: on the seven units of "
                 "versions 2 to 4, dropping the spare bytes gave exactly the entries of the "
                 "live call list files, no more and no fewer, where reading the image as "
                 "stored gave the same on two units and fewer or none on five. On the version "
                 "5 unit (2019 Ford Fusion) the image held 33 distinct documents, older and "
                 "current, with 161 distinct entries against 59 in the live files. An "
                 "independent parse of that unit listed 130 distinct calls and all 130 are "
                 "among the 161, with the same time, number and list. Entries that are also in "
                 "the live files appear here too. Call List decodes the list type as the Call "
                 "History artifact does. Call Time comes from the entry's time attribute, "
                 "which only version 5 writes, and has no time zone; it is written out as if "
                 "it were UTC with no offset applied. Documents Holding It counts the distinct "
                 "documents in the image that contain the entry. An image whose size is not a "
                 "whole number of 2,112-byte pages is not read; that was the case for the two "
                 "tested SYNC Gen2 images. An entry records that the module held this call "
                 "list entry at some time. It does not establish who used the handset.",
        "paths": ('*/LargeOutputFiles/image.nbo',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, NAND image | 14 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, NAND image | 31 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, NAND image | 83 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, NAND image | 138 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, NAND image | 154 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, NAND image | 161 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, NAND image | 0 rows, image size "
                             "is not a whole number of 2,112-byte pages, not read",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, NAND image | 0 rows, image "
                             "size is not a whole number of 2,112-byte pages, not read",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, NAND image | 123 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, NAND image | 150 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "ford_sync_wince_partition_call_history": {
        "name": "Ford SYNC WinCE - Call History In Partition Image",
        "description": "Call list entries read from the call list documents in an exFAT "
                       "partition image of the module, with the list, name, number and call "
                       "time of each entry, how many documents hold it, and whether those "
                       "documents sit in a listed file, in an allocated cluster no listed file "
                       "holds, or in a free cluster.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From DiskImages/partition<n>.img, the raw partition an acquisition carries. "
                 "The image is searched as bytes for complete call list documents, the same "
                 "<Device> XML the module keeps as Windows/phonebook/CH<address>.xml. Only a "
                 "document complete from its opening to its closing tag, in one unbroken "
                 "stretch of the image, is read. Only an exFAT image is searched, because "
                 "Where Found needs the vendored reader to read its allocation bitmap and the "
                 "files its directory tree lists. Where Found says where the documents holding "
                 "an entry sit, and lists every place when several documents hold it: 'free "
                 "cluster' is a cluster the bitmap has clear, 'in a listed file' an allocated "
                 "cluster whose document text a listed file also holds, and 'allocated "
                 "cluster, in no listed file' an allocated cluster whose document text no "
                 "listed file holds. The last two are decided by comparing text, not by "
                 "following each file's clusters. Run on two SYNC Gen2 units from their "
                 "acquisition folders. On the 2011 Ford Explorer XLT no listed file held a call "
                 "list document, and it gave 85 entries from 2 documents, 18 in free clusters and "
                 "67 in allocated clusters in no listed file. Why those clusters are allocated "
                 "is not established. The 2014 Ford Edge SEL gave 75 entries from 3 documents: "
                 "68 also in a listed file, 61 of those in a free cluster as well, and 7 only "
                 "in free clusters. Compared with an independent parse of each unit: on the "
                 "Edge its 75 distinct calls are exactly these 75 by number, list and handset; "
                 "on the Explorer all 78 of its calls are among the 85 by time, number, list "
                 "and handset, and the other 7, all in allocated clusters in no listed file, "
                 "are not in it. Entries that are also in the live call list files appear here "
                 "too. Call List decodes the list type as the Call History artifact does. Call "
                 "Time comes from the entry's time attribute and has no time zone; it is "
                 "written out as if it were UTC with no offset applied. All 85 Explorer "
                 "entries carried it and none of the 75 Edge entries did. Name held an empty "
                 "string on 46 of the 85 and 65 of the 75, where the entry carries no name. "
                 "Documents Holding It counts the distinct documents in the image that "
                 "contain the entry, and First Offset is the byte offset of the first of them. "
                 "Documents Holding It held 1 on all 85 Explorer rows and 1 to 3 on the Edge. "
                 "Handset Address held one value on all 75 Edge rows and two across the "
                 "Explorer's 85. "
                 "The eight SYNC Gen1 partition images run were FAT with 2,048-byte sectors, "
                 "which the reader does not read; they are not searched and gave no rows. An "
                 "entry records that the module held this call list entry at some time. It "
                 "does not establish who used the handset.",
        "paths": ('*/DiskImages/partition*.img',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 0 rows, "
                             "partition image is not exFAT, not searched",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 0 rows, not exFAT, not searched",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 75 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 85 rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 0 rows, not "
                             "exFAT, not searched",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
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
    rb'|DisplayHandler:ParkLampStatus = (?P<lamp>\d+)'
    rb'|PM: HandlePMRebootSourceComplete: Src=(?P<reboot>0x[0-9A-Fa-f]+)'
    rb'|SYSHEALTH: start saving retailmsg at (?P<save>\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)'
    rb'|SyncClockSvc!MFDMessageThreadProc: \(YMDhms\) '
    rb'(?P<clock>\d{1,4}/\d{1,2}/\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})'
    rb'|SyncClockSvc!MFDMessageThreadProc:  Bias = (?P<bias>-?\d+) '
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


# ---------------------------------------------------------------------------
# Where a hit sits in a partition image
# ---------------------------------------------------------------------------

_EXTRACTED_FILE = 'extracted file'
_IN_FILE = 'in a listed file'
_UNLISTED = 'allocated cluster, in no listed file'
_FREE = 'free cluster'
_NOT_READ = 'file system not read'
_PLACE_ORDER = (_EXTRACTED_FILE, _IN_FILE, _UNLISTED, _FREE, _NOT_READ)
_READ_ERRORS = (OSError, ValueError, IndexError, KeyError, struct.error)
_REGULAR_FILE = 0o100000
_FILE_TYPE_MASK = 0o170000


def _is_partition_image(path):
    return os.path.basename(os.path.dirname(path)) == 'DiskImages' and \
        os.path.basename(path).lower().endswith('.img')


class _ExfatImage:
    """The free space and the listed files of an exFAT partition image.

    Read with the vendored reader. ``readable`` is False for any other file system, for
    an image the reader cannot open, and for a volume whose allocation bitmap it does
    not find, and then nothing is said about where a hit sits.
    """

    def __init__(self, path):
        self.readable = False
        self.unread_files = 0
        self._walker = None
        self._starts = []
        self._ends = []
        try:
            self._handle = open(path, 'rb')  # pylint: disable=consider-using-with
        except OSError:
            self._handle = None
            return
        try:
            kind = qnxprobe.identify_fat(self._handle, 0)
            if kind is not None and kind[0] == 'exfat':
                walker = qnxprobe.ExfatWalker(self._handle, 0)
                free = sorted(walker.free_extents())
                if free:
                    self._walker = walker
                    self._starts = [start for start, _length in free]
                    self._ends = [start + length for start, length in free]
                    self.readable = True
        except _READ_ERRORS:
            self.readable = False

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def is_free(self, offset):
        """True when the byte at offset is in a cluster the allocation bitmap has clear."""
        index = bisect.bisect_right(self._starts, offset) - 1
        return index >= 0 and offset < self._ends[index]

    def listed_files(self):
        """The content of every file the directory tree lists, one file at a time."""
        try:
            for entry in qnxprobe.walk_all(self._walker):
                node, mode, size = entry[1], entry[2], entry[3]
                if mode & _FILE_TYPE_MASK != _REGULAR_FILE or not size:
                    continue
                try:
                    yield b''.join(self._walker.read_file(node, size))
                except _READ_ERRORS:
                    self.unread_files += 1
        except _READ_ERRORS:
            self.unread_files += 1

    def place(self, offset, text_is_listed):
        """Where one occurrence sits. An occurrence in an allocated cluster is called
        unlisted only when no listed file holds the same text."""
        if not self.readable:
            return _NOT_READ
        if self.is_free(offset):
            return _FREE
        return _IN_FILE if text_is_listed else _UNLISTED


def _places(found):
    return '; '.join(place for place in _PLACE_ORDER if place in found)


def _address(text):
    digits = text.rjust(12, '0')[-12:].lower()
    return ':'.join(digits[i:i + 2] for i in range(0, 12, 2))


def _describe(match):
    """(event, detail, value, second value) for an event line; None for a clock line."""
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
    if match.group('lamp'):
        return 'Park Lamp Status', '', int(match.group('lamp')), ''
    if match.group('reboot'):
        return 'Reboot Source', '', match.group('reboot').decode('ascii'), ''
    if match.group('phone'):
        event = 'Phone Connect' if match.group('phone').startswith(b'CONNECT') \
            else 'Phone Disconnect'
        return (event, match.group('name').decode('utf-8', 'replace'),
                _address(match.group('address').decode('ascii')), '')
    return None


def _clock_line(match):
    """(clock, kind) for a line that states a date and time, else None.

    Two lines do: the log save line, written month first, and the clock service line,
    written year first.
    """
    try:
        if match.group('save'):
            return datetime.strptime(match.group('save').decode('ascii'),
                                     '%m/%d/%Y %H:%M:%S'), 'log save line'
        if match.group('clock'):
            return datetime.strptime(match.group('clock').decode('ascii'),
                                     '%Y/%m/%d %H:%M:%S'), 'clock service line'
    except ValueError:
        return None
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
    """The clock line closest in ticks to an event, as (tick, clock, kind)."""
    best = anchors[0]
    for anchor in anchors[1:]:
        if abs(anchor[0] - tick) < abs(best[0] - tick):
            best = anchor
    return best


def _events(data):
    """Event rows of one source, each with the clock derived from the nearest clock line."""
    for run in _sessions(data):
        anchors = []
        biases = []
        for match in run:
            stated = _clock_line(match)
            if stated is not None:
                anchors.append((int(match.group('tick')),) + stated)
            elif match.group('bias'):
                biases.append((int(match.group('tick')), int(match.group('bias'))))
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
            derived = anchor_clock = kind = ''
            seconds = bias = ''
            if anchors:
                anchor_tick, clock, kind = _nearest(anchors, tick)
                seconds = round((tick - anchor_tick) / 1000.0, 1)
                derived = (clock + timedelta(milliseconds=tick - anchor_tick)).strftime(
                    '%Y-%m-%d %H:%M:%S')
                anchor_clock = clock.strftime('%Y-%m-%d %H:%M:%S')
            if biases:
                bias = _nearest(biases, tick)[1]
            yield ((derived,) + described + (tick, anchor_clock, kind, seconds, bias),
                   match.start(), bytes(match.group(0)))


def _listed_event_lines(image):
    """The text of every event line in the files an exFAT image lists."""
    lines = set()
    for content in image.listed_files():
        for match in _EVENT.finditer(content):
            if _describe(match) is not None:
                lines.add(bytes(match.group(0)))
    return lines


@artifact_processor
def ford_sync_wince_log_events(context):
    rows = {}
    source_paths = []
    for file_found, data in _sources(context):
        hits = list(_events(data))
        image = _ExfatImage(file_found) if _is_partition_image(file_found) else None
        listed = _listed_event_lines(image) if image is not None and image.readable and hits \
            else set()
        for row, offset, line in hits:
            place = _EXTRACTED_FILE if image is None else image.place(offset, line in listed)
            if row in rows:
                rows[row][0] += 1
                rows[row][3].add(place)
            else:
                rows[row] = [1, offset, file_found, {place}]
                if file_found not in source_paths:
                    source_paths.append(file_found)
        logfunc(f'Ford SYNC WinCE log events: {len(hits)} event lines in '
                f'{os.path.basename(file_found)}')
        if image is not None:
            if image.unread_files:
                logfunc(f'Ford SYNC WinCE log events: {image.unread_files} listed files of '
                        f'{os.path.basename(file_found)} could not be read')
            image.close()
    data_list = [row + (found, _places(places), offset, context.get_relative_path(path))
                 for row, (found, offset, path, places) in rows.items()]
    data_list.sort(key=lambda row: (row[0] == '', row[0], row[5]))

    data_headers = (('Derived Clock', 'datetime'), 'Event', 'Detail', 'Value (as stored)',
                    'Second Value (as stored)', 'Tick', ('Nearest Clock Line', 'datetime'),
                    'Clock Line Kind', 'Seconds From Clock Line',
                    'Clock Bias Minutes (as stored)', 'Times Found', 'Where Found', 'Offset',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Call lists in the raw NAND image
# ---------------------------------------------------------------------------

# Derived by comparison, not documented: see the Call History artifact of ford_sync_wince.
_CALL_LISTS = {'0x10000': 'Incoming', '0x20000': 'Outgoing', '0x40000': 'Missed'}
_NAND_PAGE = 2112
_NAND_DATA = 2048
_PAGES_PER_READ = 16384
_DOCUMENT_LIMIT = 65536
_DEVICE_DOCUMENT = re.compile(
    rb'<Device id="([0-9a-fA-F]{12})">([\t\r\n\x20-\x7e\x80-\xff]{0,65536}?)</Device>')
_CALL_HISTORY = re.compile(rb'<CallHistory type="([^"]*)">(.*?)</CallHistory>', re.S)
_CALL = re.compile(rb'<Call\b([^>]*?)/?>')
_ATTRIBUTE = re.compile(rb'(\w+)="([^"]*)"')


def _nand_data(path):
    """The data bytes of a NAND image in order, in pieces that overlap by one document.

    The image stores each 2,048-byte page followed by 64 spare bytes. The spare bytes
    are dropped so text that crosses a page reads on. A file whose size is not a whole
    number of 2,112-byte pages does not have that layout and is not read.
    """
    try:
        size = os.path.getsize(path)
        if size == 0 or size % _NAND_PAGE:
            return
        with open(path, 'rb') as handle:
            carry = b''
            while True:
                raw = handle.read(_NAND_PAGE * _PAGES_PER_READ)
                if not raw:
                    break
                piece = carry + b''.join(raw[i:i + _NAND_DATA]
                                         for i in range(0, len(raw), _NAND_PAGE))
                yield piece
                carry = piece[-_DOCUMENT_LIMIT - 64:]
    except OSError:
        return


def _xml_text(raw):
    text = raw.decode('utf-8', 'replace')
    for entity, char in (('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&apos;', "'"),
                         ('&amp;', '&')):
        text = text.replace(entity, char)
    return text


def _compact_time(text):
    try:
        return datetime.strptime(text, '%Y%m%dT%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


@artifact_processor
def ford_sync_wince_flash_call_history(context):
    data_list = []
    source_paths = []
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        documents = set()
        rows = {}
        for piece in _nand_data(file_found):
            for match in _DEVICE_DOCUMENT.finditer(piece):
                if match.group(0) in documents:
                    continue
                documents.add(match.group(0))
                digits = match.group(1).decode('ascii').lower()
                address = ':'.join(digits[i:i + 2] for i in range(0, 12, 2))
                for list_type, body in _CALL_HISTORY.findall(match.group(2)):
                    list_type = list_type.decode('latin-1')
                    for call in _CALL.findall(body):
                        attributes = dict(_ATTRIBUTE.findall(call))
                        key = (_compact_time(attributes.get(b'time', b'').decode('latin-1')),
                               _CALL_LISTS.get(list_type, ''), list_type,
                               _xml_text(attributes.get(b'name', b'')),
                               _xml_text(attributes.get(b'num', b'')), address)
                        rows[key] = rows.get(key, 0) + 1
        logfunc(f'Ford SYNC WinCE flash call history: {len(documents)} distinct call list '
                f'documents, {len(rows)} distinct entries in {os.path.basename(file_found)}')
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for key, found in rows.items():
            data_list.append(key + (found, relative))
    data_list.sort(key=lambda row: (row[0] == '', row[0]))

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Call List Type (as stored)',
                    'Name', 'Phone Number', 'Handset Address', 'Documents Holding It',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Call lists in an exFAT partition image
# ---------------------------------------------------------------------------

def _call_entries(document):
    """(call time, list, list type, name, number, handset address) per entry of a document."""
    digits = document.group(1).decode('ascii').lower()
    address = ':'.join(digits[i:i + 2] for i in range(0, 12, 2))
    for list_type, body in _CALL_HISTORY.findall(document.group(2)):
        list_type = list_type.decode('latin-1')
        for call in _CALL.findall(body):
            attributes = dict(_ATTRIBUTE.findall(call))
            yield (_compact_time(attributes.get(b'time', b'').decode('latin-1')),
                   _CALL_LISTS.get(list_type, ''), list_type,
                   _xml_text(attributes.get(b'name', b'')),
                   _xml_text(attributes.get(b'num', b'')), address)


@artifact_processor
def ford_sync_wince_partition_call_history(context):
    data_list = []
    source_paths = []
    for file_found, data in _sources(context):
        base = os.path.basename(file_found)
        image = _ExfatImage(file_found)
        if not image.readable:
            logfunc(f'Ford SYNC WinCE partition call history: {base} was not read as an '
                    'exFAT volume with an allocation bitmap, not searched')
            image.close()
            continue
        documents = {}
        for match in _DEVICE_DOCUMENT.finditer(data):
            documents.setdefault(bytes(match.group(0)), []).append(match.start())
        listed = set()
        if documents:
            for content in image.listed_files():
                listed.update(bytes(match.group(0))
                              for match in _DEVICE_DOCUMENT.finditer(content))
        rows = {}
        for text, offsets in documents.items():
            places = {image.place(offset, text in listed) for offset in offsets}
            for key in set(_call_entries(_DEVICE_DOCUMENT.fullmatch(text))):
                if key in rows:
                    rows[key][0] += 1
                    rows[key][1].update(places)
                    rows[key][2] = min(rows[key][2], offsets[0])
                else:
                    rows[key] = [1, set(places), offsets[0]]
        logfunc(f'Ford SYNC WinCE partition call history: {len(documents)} distinct call list '
                f'documents, {len(rows)} distinct entries in {base}')
        if image.unread_files:
            logfunc(f'Ford SYNC WinCE partition call history: {image.unread_files} listed '
                    f'files of {base} could not be read')
        image.close()
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for key, (found, places, offset) in rows.items():
            data_list.append(key + (found, _places(places), offset, relative))
    data_list.sort(key=lambda row: (row[0] == '', row[0], row[5], row[4]))

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Call List Type (as stored)',
                    'Name', 'Phone Number', 'Handset Address', 'Documents Holding It',
                    'Where Found', 'First Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
