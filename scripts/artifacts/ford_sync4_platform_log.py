"""Ford SYNC 4: selected lines of the platform log.

The module writes a rolling platform log, several megabytes a file, in which every
component logs:

    rwdata/logs/fdplog.<zone>.txt[.<n>]        the current files
    rwdata/logs/pre_fdplog.<zone>.txt[.<n>]    the files kept from before

A line is '<priority>1 <time>Z <host> <process> <pid> <component> [meta sequenceId="n"]
[...] <text>'. The time carries a Z. The log holds lines from several hundred components.
This module reports only the lines of a few whose text states something about use:
charge locations, navigation searches, positions, Wi-Fi scan results and vehicle signals.

The log files roll. On the tested unit most of the log text was in the volume's free
space, not in the files. The same lines are therefore read from two more inputs:

    <image>.<volume>.unallocated.bin    a volume's free space, as qnxprobe --unallocated
                                        writes it, with the .tsv run map beside it
    DiskImages/mmcblk0.img              the raw image, read as bytes

In neither is a file system followed. A line is found by its own shape. One scan serves
every artifact of a run, and a line found in more than one input is reported once.
"""

import hashlib
import mmap
import os
import re
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "ford_sync4_charge_locations": {
        "name": "Ford SYNC 4 - Charge Locations In Log",
        "description": "Charge locations named in the platform log's charge settings lines: "
                       "the list the line belongs to, the location id and the latitude and "
                       "longitude it carries, with the first and last time each was logged.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the module's rolling platform log. Three inputs are read, and a row "
                 "says which held it in Found In: the live log files "
                 "(rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their numbered "
                 "copies), a file of the storage volume's free space "
                 "(<image>.<volume>.unallocated.bin, as qnxprobe --unallocated writes it, with "
                 "its run map beside it), and the raw image (DiskImages/mmcblk0.img) when the "
                 "input is the acquisition folder. The log files roll. On the tested unit the "
                 "free space and the image held log lines the files no longer held. Nothing is "
                 "carved by file type and no file system is followed: a line is found by its "
                 "own shape, a date and time ending in Z, a host, a process, a component and a "
                 "sequence id. The tested log files hold lines from 524 components. Only the "
                 "lines named below are read. Tested on one Ford SYNC 4 unit. Its logical zip "
                 "holds log lines dated on three days, 2024-03-27 to 2024-03-29, and 2,034 "
                 "lines dated 1970-01-01; its raw image holds 718,195 log lines against about "
                 "107,000 in the files, and 85 percent of them sit in blocks the volume marks "
                 "free. Each line's time carries a Z and is reported as the line states it; a "
                 "line dated 1970 is reported with an empty time, and no reported row on the "
                 "tested unit had one. A line found in more than one input is reported once. "
                 "Rows come from the evChargeSettings lines 'handleSavedChargeLocationMsg' and "
                 "'handleUnsavedChargeLocationMsg', which carry a location id and two whole "
                 "numbers. Identical values are folded into one row with the number of lines "
                 "and the first and last log time. The logical zip gave 21 rows from 259 "
                 "lines; the raw image gave 27 rows from 1,899 lines, from 2023-05-22 to "
                 "2024-03-28, 12 from the saved list and 15 from the unsaved list. The numbers "
                 "are degrees times 1,000,000: in the tested log files, four decimal "
                 "coordinate pairs the same component logged on other lines equal four of "
                 "these pairs divided by that. Four rows, all from the unsaved list, held a "
                 "position; all but one of the others held 128048575 and 256048575 or zeros, "
                 "and one held the first number with a different second number. Those are not "
                 "read as a position (the large numbers are outside the range of a coordinate) "
                 "and what they stand for is not established here, so their Latitude and "
                 "Longitude are left empty and the stored numbers are still shown. What the "
                 "module means by saved and unsaved is not documented here; the names are the "
                 "log's own. A block can end in the middle of a line. In a free space file "
                 "with its run map present, a line is not read across two runs that were not "
                 "neighbours on the disk (without the map the file is read as one stretch and "
                 "the run log says so), and in an image an unfinished line is cut where the "
                 "next one starts. A line cut that way is reported as far as it reads, so a "
                 "handful of rows can differ between inputs: on the tested unit the image and "
                 "the other two inputs together differed by zero to two rows per artifact. A "
                 "row records that the module logged that location for the vehicle's charge "
                 "settings. It does not establish that the vehicle was there, or when.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 21 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 27 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
    "ford_sync4_nav_searches": {
        "name": "Ford SYNC 4 - Navigation Searches In Log",
        "description": "Navigation searches named in the platform log's analytics lines, one "
                       "row per search id, with the search type and options, the number of "
                       "result lines, the provider and the logged duration.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the module's rolling platform log. Three inputs are read, and a row "
                 "says which held it in Found In: the live log files "
                 "(rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their numbered "
                 "copies), a file of the storage volume's free space "
                 "(<image>.<volume>.unallocated.bin, as qnxprobe --unallocated writes it, with "
                 "its run map beside it), and the raw image (DiskImages/mmcblk0.img) when the "
                 "input is the acquisition folder. The log files roll. On the tested unit the "
                 "free space and the image held log lines the files no longer held. Nothing is "
                 "carved by file type and no file system is followed: a line is found by its "
                 "own shape, a date and time ending in Z, a host, a process, a component and a "
                 "sequence id. The tested log files hold lines from 524 components. Only the "
                 "lines named below are read. Tested on one Ford SYNC 4 unit. Its logical zip "
                 "holds log lines dated on three days, 2024-03-27 to 2024-03-29, and 2,034 "
                 "lines dated 1970-01-01; its raw image holds 718,195 log lines against about "
                 "107,000 in the files, and 85 percent of them sit in blocks the volume marks "
                 "free. Each line's time carries a Z and is reported as the line states it; a "
                 "line dated 1970 is reported with an empty time, and no reported row on the "
                 "tested unit had one. A line found in more than one input is reported once. "
                 "Rows come from the navigation application's analytics lines: a header naming "
                 "the event (search started, resultFound or complete) followed by a line of "
                 "attributes, paired in time order and grouped on the search id. The logical "
                 "zip gave 30 rows; the raw image gave 98, from 2023-06-12 to 2024-03-29, 78 "
                 "with a start line and 20 without. The log states that the position and text "
                 "attributes are redacted, and in the analytics lines read here they are: "
                 "those lines name the attributes and carry no values, so none is reported. "
                 "What remains is the search type (Coordinate 32, POI 21, Category 16, "
                 "SavedPlace 9 on the image), the options, a POI category, the isASRSearch "
                 "value (the same on every row of the tested unit), the provider and the "
                 "duration in milliseconds, all as stored. Result Lines counts the resultFound "
                 "lines for that search id, up to 167. A block can end in the middle of a "
                 "line. In a free space file with its run map present, a line is not read "
                 "across two runs that were not neighbours on the disk (without the map the "
                 "file is read as one stretch and the run log says so), and in an image an "
                 "unfinished line is cut where the next one starts. A line cut that way is "
                 "reported as far as it reads, so a handful of rows can differ between inputs: "
                 "on the tested unit the image and the other two inputs together differed by "
                 "zero to two rows per artifact. A row records that the navigation application "
                 "logged a search. It does not establish what was searched for or who "
                 "searched.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 30 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 98 rows",
        },
        "output_types": "standard",
        "artifact_icon": "search",
    },
    "ford_sync4_positions": {
        "name": "Ford SYNC 4 - Positions In Log",
        "description": "Positions in the platform log's lbs component lines, each with its log "
                       "time, the kind of line it came from and the result, altitude or "
                       "heading the line states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the module's rolling platform log. Three inputs are read, and a row "
                 "says which held it in Found In: the live log files "
                 "(rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their numbered "
                 "copies), a file of the storage volume's free space "
                 "(<image>.<volume>.unallocated.bin, as qnxprobe --unallocated writes it, with "
                 "its run map beside it), and the raw image (DiskImages/mmcblk0.img) when the "
                 "input is the acquisition folder. The log files roll. On the tested unit the "
                 "free space and the image held log lines the files no longer held. Nothing is "
                 "carved by file type and no file system is followed: a line is found by its "
                 "own shape, a date and time ending in Z, a host, a process, a component and a "
                 "sequence id. The tested log files hold lines from 524 components. Only the "
                 "lines named below are read. Tested on one Ford SYNC 4 unit. Its logical zip "
                 "holds log lines dated on three days, 2024-03-27 to 2024-03-29, and 2,034 "
                 "lines dated 1970-01-01; its raw image holds 718,195 log lines against about "
                 "107,000 in the files, and 85 percent of them sit in blocks the volume marks "
                 "free. Each line's time carries a Z and is reported as the line states it; a "
                 "line dated 1970 is reported with an empty time, and no reported row on the "
                 "tested unit had one. A line found in more than one input is reported once. "
                 "Rows come from two lines of the lbs component: 'Trimble Output res=<result> "
                 "lat=, lon=, alt=' and 'UbloxReader: lat = , lon = , heading = '. Latitude "
                 "and longitude are the decimal numbers the line prints as lat and lon, with "
                 "no unit stated; all were within the range of degrees on the tested unit. The "
                 "logical zip gave 120 rows; the raw image gave 2,381, 1,716 from the first "
                 "line and 665 from the second, from 2023-07 to 2024-03 with 2,284 of them in "
                 "2024-03. Result is the first line's own word, Success on 1,632 rows and "
                 "Failure on 84; a Failure row, three of which have a latitude of zero, is "
                 "reported as the log states it and should not be read as a fix. The raw-image "
                 "rows were compared with a list of log lines from the same image made by "
                 "another tool (a file kept beside the image, its maker not recorded): 2,377 "
                 "of its 2,378 distinct positions are among them with the same time and "
                 "coordinates. Which receiver or computation each line reports, and how the "
                 "two relate, is not established here; the labels are the log's own words. "
                 "Times Found counts how often the same line was found. A block can end in the "
                 "middle of a line. In a free space file with its run map present, a line is "
                 "not read across two runs that were not neighbours on the disk (without the "
                 "map the file is read as one stretch and the run log says so), and in an "
                 "image an unfinished line is cut where the next one starts. A line cut that "
                 "way is reported as far as it reads, so a handful of rows can differ between "
                 "inputs: on the tested unit the image and the other two inputs together "
                 "differed by zero to two rows per artifact. A row records that the module "
                 "logged that position at that time. It does not establish who was driving.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 120 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 2381 rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "ford_sync4_wifi_access_points": {
        "name": "Ford SYNC 4 - Wi-Fi Access Points In Log",
        "description": "Wi-Fi access points named in the platform log's CM component scan "
                       "result lines, one row for each network name and address, with the "
                       "first and last time it was logged, the number of lines, the strongest "
                       "signal and the channels.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the module's rolling platform log. Three inputs are read, and a row "
                 "says which held it in Found In: the live log files "
                 "(rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their numbered "
                 "copies), a file of the storage volume's free space "
                 "(<image>.<volume>.unallocated.bin, as qnxprobe --unallocated writes it, with "
                 "its run map beside it), and the raw image (DiskImages/mmcblk0.img) when the "
                 "input is the acquisition folder. The log files roll. On the tested unit the "
                 "free space and the image held log lines the files no longer held. Nothing is "
                 "carved by file type and no file system is followed: a line is found by its "
                 "own shape, a date and time ending in Z, a host, a process, a component and a "
                 "sequence id. The tested log files hold lines from 524 components. Only the "
                 "lines named below are read. Tested on one Ford SYNC 4 unit. Its logical zip "
                 "holds log lines dated on three days, 2024-03-27 to 2024-03-29, and 2,034 "
                 "lines dated 1970-01-01; its raw image holds 718,195 log lines against about "
                 "107,000 in the files, and 85 percent of them sit in blocks the volume marks "
                 "free. Each line's time carries a Z and is reported as the line states it; a "
                 "line dated 1970 is reported with an empty time, and no reported row on the "
                 "tested unit had one. A line found in more than one input is reported once. "
                 "Rows come from the CM component's scan result lines, 'ap[n] ssid = , bssid = "
                 ", sec = , rssi = , chan = '. The log wraps the name and the address in <SD2> "
                 "markers, which are removed. Lines are folded on the name and address. The "
                 "logical zip gave 2 rows; the raw image gave 164 rows from 759 lines, from "
                 "2023-05-22 to 2024-03-29, every one with a name and a six-byte address. The "
                 "raw-image rows were compared with a list of log lines from the same image "
                 "made by another tool (a file kept beside the image, its maker not recorded): "
                 "all 164 of its distinct name and address pairs are among them. Strongest "
                 "Signal is the highest rssi among the lines, and Security Values are the sec "
                 "numbers seen, as stored; nothing available here documents the sec numbers. A "
                 "row records that the module logged that access point in a scan result with a "
                 "signal value. It does not establish that the module connected to it. A block "
                 "can end in the middle of a line. In a free space file with its run map "
                 "present, a line is not read across two runs that were not neighbours on the "
                 "disk (without the map the file is read as one stretch and the run log says "
                 "so), and in an image an unfinished line is cut where the next one starts. A "
                 "line cut that way is reported as far as it reads, so a handful of rows can "
                 "differ between inputs: on the tested unit the image and the other two inputs "
                 "together differed by zero to two rows per artifact.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 2 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 164 rows",
        },
        "output_types": "standard",
        "artifact_icon": "wifi",
    },
    "ford_sync4_vehicle_signals": {
        "name": "Ford SYNC 4 - Vehicle Signals In Log",
        "description": "Vehicle signal lines in the platform log: door status, gear position, "
                       "odometer value, current street and ignition with driver door, each "
                       "with its log time and the values the line states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the module's rolling platform log. Three inputs are read, and a row "
                 "says which held it in Found In: the live log files "
                 "(rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their numbered "
                 "copies), a file of the storage volume's free space "
                 "(<image>.<volume>.unallocated.bin, as qnxprobe --unallocated writes it, with "
                 "its run map beside it), and the raw image (DiskImages/mmcblk0.img) when the "
                 "input is the acquisition folder. The log files roll. On the tested unit the "
                 "free space and the image held log lines the files no longer held. Nothing is "
                 "carved by file type and no file system is followed: a line is found by its "
                 "own shape, a date and time ending in Z, a host, a process, a component and a "
                 "sequence id. The tested log files hold lines from 524 components. Only the "
                 "lines named below are read. Tested on one Ford SYNC 4 unit. Its logical zip "
                 "holds log lines dated on three days, 2024-03-27 to 2024-03-29, and 2,034 "
                 "lines dated 1970-01-01; its raw image holds 718,195 log lines against about "
                 "107,000 in the files, and 85 percent of them sit in blocks the volume marks "
                 "free. Each line's time carries a Z and is reported as the line states it; a "
                 "line dated 1970 is reported with an empty time, and no reported row on the "
                 "tested unit had one. A line found in more than one input is reported once. "
                 "Rows come from five lines: the navigation engine's sigDoorStatus, "
                 "sigGearPosition and sigSetOdometerValue lines, the navigation service's "
                 "current street line, and a line that states the driver door and ignition "
                 "status together. Values is the text of the line after its label, with a "
                 "trailing 'successful' removed from street lines: door lines give a number "
                 "for each door and the tailgate, gear and ignition lines a number, odometer "
                 "lines a number with no unit stated, and street lines three labelled fields, "
                 "the first a name that can be empty. Nothing available here documents the "
                 "numbers, so none is relabelled. The logical zip gave 18 rows; the raw image "
                 "gave 370 from 2023-07-18 to 2024-03-29: gear 193, door 108, odometer 31, "
                 "current street 19, ignition with driver door 19. Three of the 108 door rows "
                 "on the image were cut lines and carry unrelated text after the first value. "
                 "The door, gear and odometer rows were compared with a list of log lines from "
                 "the same image made by another tool (a file kept beside the image, its maker "
                 "not recorded): 318 of its 319 distinct lines are among them. Times Found "
                 "counts how often the same line was found. A block can end in the middle of a "
                 "line. In a free space file with its run map present, a line is not read "
                 "across two runs that were not neighbours on the disk (without the map the "
                 "file is read as one stretch and the run log says so), and in an image an "
                 "unfinished line is cut where the next one starts. A line cut that way is "
                 "reported as far as it reads, so a handful of rows can differ between inputs: "
                 "on the tested unit the image and the other two inputs together differed by "
                 "zero to two rows per artifact. A row records that the module logged that "
                 "line. It does not establish who opened a door or drove the vehicle.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 18 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 370 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
}

_LINE = re.compile(
    rb'(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?Z \S+ \S+ \d+ (\S+) '
    rb'\[meta sequenceId="(\d+)"\]\[[^\]\n]{0,60}\] ?([^\n\x00]{0,600})')
# The start of a line, for finding one that an unfinished line ran into.
_LINE_START = re.compile(rb'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z \S+ \S+ \d+ \S+ \[meta ')
_CHARGE = re.compile(r'handle(Saved|Unsaved)ChargeLocationMsg: ChrgLocId_D_\w+: (\d+) '
                     r'ChrgLocLatt_An_\w+: (-?\d+) ChrgLocLong_An_\w+: (-?\d+)')
_ANALYTICS_HEAD = re.compile(r'hmi\.analytics: ---\[ (\w+) \]-----\( (\w+) \)---')
_ANALYTICS_ATTRS = re.compile(r'hmi\.analytics: Attributes: (.*)$')
_ATTR = re.compile(r'\[(\w+): ([^\]]*)\]')
_TRIMBLE = re.compile(r'^Trimble Output res=(\w+) lat=(-?[\d.]+), lon=(-?[\d.]+), alt=(-?[\d.]+)')
_UBLOX = re.compile(r'^UbloxReader: lat = (-?[\d.]+), lon = (-?[\d.]+), heading = (-?[\d.]+)')
_ACCESS_POINT = re.compile(r'ap\[\d+\] ssid = "(.*?)", bssid = (\S+?), sec = (\d+), '
                           r'rssi = (-?\d+),\s+chan = (\d+)')
_MARKER = re.compile(r'</?SD2>')
_SIGNALS = (
    ('nav.enginelib', re.compile(r'sigDoorStatus to nav app, (.*)$'), 'Door status'),
    ('nav.enginelib', re.compile(r'sigGearPosition to nav app, (.*)$'), 'Gear position'),
    ('nav.enginelib', re.compile(r'sigSetOdometerValue to nav app, (.*)$'), 'Odometer value'),
    ('nav.service', re.compile(r'sync_publish_nav_current_street: publish message\s+(.*?)'
                               r'(?: successful)?$'), 'Current street'),
    ('redcap', re.compile(r'handle_ignition_and_door_status \S+ \S+ (.*)$'),
     'Ignition and driver door'),
)
_DEGREE = 1000000
_LOG_FILE = 'Log file'
_FREE_SPACE = 'Free space file'
_RAW_IMAGE = 'Raw image'
# One scan of a 29 GiB image takes minutes, so the lines kept from a set of inputs are
# held here for the other artifacts of the same run.
_SCANNED = {}


def _kept(component, text):
    """True for the lines some artifact of this module reports."""
    if component == 'lbs':
        return text.startswith(('Trimble Output', 'UbloxReader: lat'))
    if component == 'CM':
        return ' ssid = ' in text
    if component == 'evChargeSettings':
        return 'ChargeLocationMsg' in text
    if component == 'vendor.garmin':
        return 'hmi.analytics' in text
    return any(component == name and pattern.search(text) for name, pattern, _ in _SIGNALS)


def _source_kind(path):
    base = os.path.basename(path)
    if 'fdplog' in base:
        return _LOG_FILE
    if base.endswith('.unallocated.bin'):
        return _FREE_SPACE
    return _RAW_IMAGE


def _runs(path, size):
    """(start, end) of each stretch of an input that was contiguous in the image.

    A free space file is free runs written one after another, so two neighbours in the
    file were not neighbours on the disk, and a line read across the join would be made
    of two unrelated pieces. The map the writer puts beside the file gives the joins;
    without it the file is read as one stretch and the run log says so.
    """
    if _source_kind(path) != _FREE_SPACE:
        return [(0, size)]
    map_path = path[:-len('.bin')] + '.tsv'
    runs = []
    try:
        with open(map_path, encoding='utf-8') as handle:
            for line in handle.read().splitlines()[1:]:
                start, _, length = line.split('\t')
                runs.append((int(start), int(start) + int(length)))
    except (OSError, ValueError):
        runs = []
    if not runs or runs[-1][1] != size:
        logfunc(f'Ford SYNC 4 platform log: no usable run map beside '
                f'{os.path.basename(path)}; a line read across two free runs cannot be '
                'told from a real one')
        return [(0, size)]
    return runs


def _matches(mapped, runs):
    """(match, text bytes) for each line in each stretch.

    A block can end in the middle of a line. In an image the next block then starts
    another line with no newline between the two, and the unfinished line's text would
    run on into it. The text is cut where a new line starts, and the search goes on
    from there, so the second line is found as well.
    """
    for start, end in runs:
        position = start
        while position < end:
            match = _LINE.search(mapped, position, end)
            if match is None:
                break
            text = match.group(10)
            inner = _LINE_START.search(text)
            if inner:
                text = text[:inner.start()]
                position = match.start(10) + inner.start()
            else:
                position = max(match.end(), match.start() + 1)
            yield match, text


def _scan(path):
    """(log time, time text, component, sequence id, text) for each kept line of one input.

    The input is mapped, not read, and a line is found by its own shape, so the same
    reader serves a log file, a file of free space and a raw image.
    """
    try:
        size = os.path.getsize(path)
        if not size:
            return
        handle = open(path, 'rb')  # pylint: disable=consider-using-with
    except OSError:
        return
    try:
        mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
    except (OSError, ValueError):
        handle.close()
        return
    try:
        for match, raw_text in _matches(mapped, _runs(path, size)):
            component = match.group(8).decode('utf-8', 'replace')
            text = raw_text.decode('utf-8', 'replace').rstrip('\r ')
            if not _kept(component, text):
                continue
            year, month, day, hour, minute, second = (int(v) for v in match.groups()[:6])
            stamp = ''
            if year != 1970:
                try:
                    stamp = datetime(year, month, day, hour, minute,
                                     second).strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    stamp = ''
            exact = match.group(0)[:27].decode('ascii', 'replace')
            yield stamp, exact, component, int(match.group(9)), text
    finally:
        mapped.close()
        handle.close()


def _log_lines(context):
    """Kept lines of every matched input, each once, oldest first.

    Returns (lines, source paths). A line is (log time, component, text, found in, times
    found, sequence id); 'found in' names the kinds of input that held it.
    """
    # the .tsv beside a free space file is its run map, read with it and not as a source
    paths = sorted(str(f) for f in set(context.get_files_found())
                   if not os.path.isdir(str(f)) and not str(f).endswith('.unallocated.tsv'))
    key = tuple((path, os.path.getsize(path)) for path in paths if os.path.exists(path))
    if key in _SCANNED:
        return _SCANNED[key]
    merged = {}
    used = []
    seen_content = set()
    for path in paths:
        kind = _source_kind(path)
        if kind == _LOG_FILE:
            # The current and kept log files can be the same file twice.
            try:
                with open(path, 'rb') as handle:
                    digest = hashlib.sha256(handle.read()).digest()
            except OSError:
                continue
            if digest in seen_content:
                continue
            seen_content.add(digest)
        found = False
        for stamp, exact, component, sequence, text in _scan(path):
            found = True
            entry = merged.setdefault((exact, component, sequence, text),
                                      [stamp, set(), 0])
            entry[1].add(kind)
            entry[2] += 1
        if found:
            used.append(path)
        if kind != _LOG_FILE:
            logfunc(f'Ford SYNC 4 platform log: read {os.path.basename(path)} as '
                    f'{kind.lower()}')
    lines = [(entry[0], component, text, ', '.join(sorted(entry[1])), entry[2], sequence)
             for (exact, component, sequence, text), entry in sorted(merged.items())]
    _SCANNED.clear()
    _SCANNED[key] = (lines, used)
    return lines, used


def _found_in(kinds):
    return ', '.join(sorted(kinds))


@artifact_processor
def ford_sync4_charge_locations(context):
    lines, sources = _log_lines(context)
    found = {}
    for stamp, component, text, where, _times, _sequence in lines:
        if component != 'evChargeSettings':
            continue
        match = _CHARGE.search(text)
        if not match:
            continue
        key = (match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)))
        entry = found.setdefault(key, ['', '', 0, set()])
        if stamp:
            entry[0] = min(entry[0], stamp) if entry[0] else stamp
            entry[1] = max(entry[1], stamp)
        entry[2] += 1
        entry[3].update(where.split(', '))

    data_list = []
    for (kind, number, latitude, longitude), (first, last, count, kinds) in sorted(
            found.items()):
        in_range = abs(latitude) <= 90 * _DEGREE and abs(longitude) <= 180 * _DEGREE \
            and (latitude or longitude)
        data_list.append((first, last, kind, number,
                          latitude / _DEGREE if in_range else '',
                          longitude / _DEGREE if in_range else '',
                          latitude, longitude, count, _found_in(kinds)))

    data_headers = (('First Log Time', 'datetime'), ('Last Log Time', 'datetime'), 'List',
                    'Location ID', 'Latitude', 'Longitude', 'Latitude (as stored)',
                    'Longitude (as stored)', 'Lines', 'Found In')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_nav_searches(context):
    lines, sources = _log_lines(context)
    searches = {}
    order = []
    pending = None
    for stamp, component, text, where, _times, _sequence in lines:
        if component != 'vendor.garmin' or 'hmi.analytics' not in text:
            continue
        head = _ANALYTICS_HEAD.search(text)
        if head:
            pending = (stamp, head.group(2)) if head.group(1) == 'search' else None
            continue
        attrs = _ANALYTICS_ATTRS.search(text)
        if not attrs or pending is None:
            continue
        values = dict(_ATTR.findall(attrs.group(1)))
        uid = values.get('searchUID', '').strip()
        when, action = pending
        pending = None
        if not uid:
            continue
        if uid not in searches:
            searches[uid] = {'started': '', 'completed': '', 'first result': '', 'results': 0,
                             'where': set()}
            order.append(uid)
        entry = searches[uid]
        entry['where'].update(where.split(', '))
        if action == 'started':
            entry['started'] = when
            for name in ('searchType', 'searchOptions', 'isASRSearch', 'poiCategory'):
                entry[name] = values.get(name, '').strip()
        elif action == 'resultFound':
            entry['results'] += 1
            entry['first result'] = entry['first result'] or when
            entry['searchProvider'] = values.get('searchProvider', '').strip()
        elif action == 'complete':
            entry['completed'] = when
            entry['durationMs'] = values.get('durationMs', '').strip()

    data_list = []
    for uid in order:
        entry = searches[uid]
        data_list.append((entry['started'] or entry['first result'] or entry['completed'],
                          entry['completed'], entry.get('searchType', ''),
                          entry.get('searchOptions', ''), entry.get('poiCategory', ''),
                          entry.get('isASRSearch', ''), entry['results'],
                          entry.get('searchProvider', ''), entry.get('durationMs', ''),
                          'Yes' if entry['started'] else 'No', uid,
                          _found_in(entry['where'])))

    data_headers = (('First Log Time', 'datetime'), ('Complete Log Time', 'datetime'),
                    'Search Type', 'Search Options', 'POI Category', 'isASRSearch (as stored)',
                    'Result Lines', 'Search Provider', 'Duration Milliseconds (as stored)',
                    'Start Line Found', 'Search ID', 'Found In')
    return data_headers, data_list, '\n'.join(sources)


def _number(text):
    try:
        return float(text)
    except ValueError:
        return ''


@artifact_processor
def ford_sync4_positions(context):
    lines, sources = _log_lines(context)
    data_list = []
    for stamp, component, text, where, times, _sequence in lines:
        if component != 'lbs':
            continue
        trimble = _TRIMBLE.match(text)
        ublox = None if trimble else _UBLOX.match(text)
        if trimble:
            data_list.append((stamp, _number(trimble.group(2)), _number(trimble.group(3)),
                              'Trimble Output', trimble.group(1), trimble.group(4), '', where,
                              times))
        elif ublox:
            data_list.append((stamp, _number(ublox.group(1)), _number(ublox.group(2)),
                              'UbloxReader', '', '', ublox.group(3), where, times))

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Line Kind',
                    'Result (as stored)', 'Altitude (as stored)', 'Heading (as stored)',
                    'Found In', 'Times Found')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_wifi_access_points(context):
    lines, sources = _log_lines(context)
    found = {}
    for stamp, component, text, where, _times, _sequence in lines:
        if component != 'CM':
            continue
        match = _ACCESS_POINT.search(text)
        if not match:
            continue
        name = _MARKER.sub('', match.group(1))
        address = _MARKER.sub('', match.group(2))
        entry = found.setdefault((name, address), ['', '', 0, None, set(), set(), set()])
        if stamp:
            entry[0] = min(entry[0], stamp) if entry[0] else stamp
            entry[1] = max(entry[1], stamp)
        entry[2] += 1
        signal = int(match.group(4))
        entry[3] = signal if entry[3] is None else max(entry[3], signal)
        entry[4].add(match.group(5))
        entry[5].add(match.group(3))
        entry[6].update(where.split(', '))

    data_list = [(first, last, name, address, count, strongest,
                  ', '.join(sorted(channels, key=int)), ', '.join(sorted(security, key=int)),
                  _found_in(kinds))
                 for (name, address), (first, last, count, strongest, channels, security,
                                       kinds) in sorted(found.items())]

    data_headers = (('First Log Time', 'datetime'), ('Last Log Time', 'datetime'),
                    'Network Name', 'Access Point Address', 'Lines',
                    'Strongest Signal (as stored)', 'Channels', 'Security Values (as stored)',
                    'Found In')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_vehicle_signals(context):
    lines, sources = _log_lines(context)
    data_list = []
    for stamp, component, text, where, times, _sequence in lines:
        for name, pattern, label in _SIGNALS:
            if component != name:
                continue
            match = pattern.search(text)
            if match:
                data_list.append((stamp, label, match.group(1).strip(), where, times))
                break

    data_headers = (('Log Time', 'datetime'), 'Signal', 'Values (as stored)', 'Found In',
                    'Times Found')
    return data_headers, data_list, '\n'.join(sources)
