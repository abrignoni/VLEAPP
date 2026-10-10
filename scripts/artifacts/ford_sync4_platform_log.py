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
        "version": "0.3",
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
                 "next one starts. A line that does not run to a newline is not reported here, "
                 "because the longitude can be the line's last value (131 of 265 such lines in "
                 "the tested log files) and can then be cut with it. On the tested unit the "
                 "image gave the same 27 rows and line counts with and without that rule. A "
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
        "version": "0.3",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-10",
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
                 "free. Each line's time carries a Z and is reported to the second as the line "
                 "states it; a line dated 1970 is reported with an empty time, and no reported "
                 "row on the tested unit had one. A line found in more than one input is "
                 "reported once. Rows come from four lines of the lbs component: 'Trimble "
                 "Input lat=, lon=, alt=', 'Trimble Output res=<result> lat=, lon=, alt=', "
                 "'UbloxReader: lat = , lon = , heading = ' and 'Raw GPS: latitude= , "
                 "longitude= '. Latitude and longitude are the decimal numbers the line prints "
                 "as lat and lon (latitude and longitude on the Raw GPS line), with no unit "
                 "stated; all were within the range of degrees on the tested unit. The logical "
                 "zip gave 214 rows; the raw image gave 4,283, from 2023-07 to 2024-03 with "
                 "4,133 of them in 2024-03: Trimble Input 1,716, Trimble Output 1,716, "
                 "UbloxReader 665 and Raw GPS 186. Result is the Trimble Output line's own "
                 "word, Success on 1,632 rows and Failure on 84; a Failure row, three of which "
                 "have a latitude of zero, is reported as the log states it and should not be "
                 "read as a fix. Eight Trimble Input rows also have a latitude of zero. The "
                 "raw-image rows were compared with a strings listing kept beside the image (a "
                 "Sysinternals Strings output, by its header): 2,377 of its 2,378 distinct "
                 "positions are among them with the same time and coordinates; that comparison "
                 "was made on the Trimble Output and UbloxReader rows, before the other two "
                 "lines were read. Which receiver or computation each line reports, and how "
                 "the two relate, is not established here; the labels are the log's own words. "
                 "Times Found counts how often the same line was found. A block can end in the "
                 "middle of a line. In a free space file with its run map present, a line is "
                 "not read across two runs that were not neighbours on the disk (without the "
                 "map the file is read as one stretch and the run log says so), and in an "
                 "image an unfinished line is cut where the next one starts. A line that does "
                 "not run to a newline keeps its latitude and longitude, which a separator "
                 "follows, and its last value, the altitude or heading, is left empty: two "
                 "rows on the tested unit's image. A Raw GPS line ends with its longitude, so "
                 "a cut Raw GPS line is not reported. A handful of rows can differ between "
                 "inputs: on the tested unit the image and the other two inputs together "
                 "differed by two rows. A row records that the module logged that position at "
                 "that time. It does not establish who was driving.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 214 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 4283 rows",
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
                 "Rows come from the CM component's scan result lines, 'ap[n] ssid = , bssid = "
                 ", sec = , rssi = , chan = '. The log wraps the name and the address in <SD2> "
                 "markers, which are removed. Lines are folded on the name and address. The "
                 "logical zip gave 2 rows; the raw image gave 164 rows from 759 lines, from "
                 "2023-05-22 to 2024-03-29, every one with a name and a six-byte address. The "
                 "raw-image rows were compared with a strings listing kept beside the image (a "
                 "Sysinternals Strings output, by its header): all 164 of its distinct name "
                 "and address pairs are among them. Strongest Signal is the highest rssi among "
                 "the lines, and Security Values are the sec numbers seen, as stored; nothing "
                 "available here documents the sec numbers. A row records that the module "
                 "logged that access point in a scan result with a signal value. It does not "
                 "establish that the module connected to it. A block can end in the middle of "
                 "a line. In a free space file with its run map present, a line is not read "
                 "across two runs that were not neighbours on the disk (without the map the "
                 "file is read as one stretch and the run log says so), and in an image an "
                 "unfinished line is cut where the next one starts. A line that does not run "
                 "to a newline still counts toward its access point when it reads as far as "
                 "the channel, but its channel is not taken from it. On the tested unit the "
                 "image gave the same 164 rows with and without that rule.",
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
                       "odometer value, current street, ignition with driver door, tire "
                       "pressures, driver distraction state and the odometer in a vehicle data "
                       "notification, each with its log time and the values the line states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.3",
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
                 "status together. Three more were added: the navigation service's 'Received "
                 "new tire pressures' line, and the AppLinkService JSON notifications "
                 "UI.OnDriverDistraction, for its state, and VehicleInfo.OnVehicleData when it "
                 "carries only an odometer value. Values is the text of the line after its "
                 "label, with a trailing 'successful' removed from street lines: door lines "
                 "give a number for each door and the tailgate, gear and ignition lines a "
                 "number, odometer lines a number with no unit stated, street lines three "
                 "labelled fields, the first a name that can be empty, tire pressure lines "
                 "four numbers with no unit stated, and the two notifications the state word "
                 "or the odometer number. Nothing available here documents the numbers, so "
                 "none is relabelled. The logical zip gave 27 rows; the raw image gave 817 "
                 "from 2023-07-18 to 2024-03-29: tire pressures 241, gear 193, driver "
                 "distraction state 189 (DD_OFF 99, DD_ON 90), door 107, odometer 31, current "
                 "street 19, ignition with driver door 19, odometer in a vehicle data "
                 "notification 18. The door, gear and odometer rows were compared with a "
                 "strings listing kept beside the image (a Sysinternals Strings output, by its "
                 "header): 316 of its 319 lines, counted as distinct by time to the second, "
                 "signal and values, are among them, and the other three are door lines that "
                 "list holds with the text that followed the cut. Times Found counts how often "
                 "the same line was found. A block can end in the middle of a line. In a free "
                 "space file with its run map present, a line is not read across two runs that "
                 "were not neighbours on the disk (without the map the file is read as one "
                 "stretch and the run log says so), and in an image an unfinished line is cut "
                 "where the next one starts. What follows a cut line is whatever the next "
                 "block holds, which can be other text with its own newline. A door, gear, "
                 "odometer or tire pressure line is therefore reported whole only when it runs "
                 "to a newline and holds nothing but 'name = number' values. From any other "
                 "one, only the values at its start that a separator follows are kept and "
                 "Whole Line says No, and a line with no such value is not reported. A current "
                 "street or ignition line that does not run to a newline is reported as far as "
                 "it reads and Whole Line says No. A driver distraction or vehicle data "
                 "notification is reported only when the line ends with its closing brackets, "
                 "so one that is cut or has other text after it is not reported. On the tested "
                 "unit's image two door rows and one tire pressure row say No, and one door "
                 "line was not reported. A row records that the module logged that line. It "
                 "does not establish who opened a door or drove the vehicle.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 27 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 817 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
    "ford_sync4_power_events": {
        "name": "Ford SYNC 4 - Power Manager Events In Log",
        "description": "Power manager lines in the platform log that name an event: ignition, "
                       "engine off, door ajar and the other events the line names, CAN event "
                       "lines, the ignition status and the remote start status, each with its "
                       "log time and the value the line states.",
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
                 "line dated 1970 is reported with an empty time: 8 of the reported rows on "
                 "the tested unit, in the logical zip and in the raw image. A line found in "
                 "more than one input is reported once. Rows come from the PowerManager "
                 "components' lines 'event <name>, EventValue = <n>', 'CAN event: <text>', "
                 "'BodyInfo_HS<n>.Ignition_Status=<n>' and 'Remote_Start_Status is <word>'. "
                 "Event is the name the line gives, or CAN event, and Value is the number or "
                 "text the line states, as stored. Nothing available here documents the "
                 "numbers, so none is relabelled. The logical zip gave 158 rows; the raw image "
                 "gave 1,359, of which 1,351 are dated, from 2023-07-18 to 2024-03-29: "
                 "IgnitionOnEvent 320, CAN event 231, Ignition_Status 177, IlluminationEvent "
                 "167, TransportmodeEvent 166, Remote_Start_Status 164, DriverDoorAjarEvent "
                 "45, EngineOffEvent 27, eCallEvent 23, LBIEvent 17, KeyOffPwMdeEvent 12, "
                 "PassengerDoorAjarEvent 10. Both distinct CAN event texts on the tested unit "
                 "name a door. A row records that the power manager logged that event. It does "
                 "not establish who opened a door or switched the ignition. A row is reported "
                 "only for a line that runs to a newline and matches the whole of a shape "
                 "named here. A line cut at the end of a block is still reported if the next "
                 "block begins with a newline and the shortened text fits the shape; that was "
                 "not seen on the tested unit. Times Found counts how often the same line was "
                 "found. In a free space file with its run map present, a line is not read "
                 "across two runs that were not neighbours on the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 158 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 1359 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_sync4_battery_voltage": {
        "name": "Ford SYNC 4 - Battery Voltage Lines In Log",
        "description": "Battery voltage lines the power manager wrote to the platform log, "
                       "each with its log time and the three numbers the line states.",
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
                 "Rows come from the PowerManager line 'Batt Voltage = <n>, PwrCurTargetState "
                 "= <n>, Lvi_Flag =<n>'. The three numbers are as stored: the line states no "
                 "unit and nothing available here documents them. The logical zip gave 133 "
                 "rows; the raw image gave 2,148 from 2023-07-18 to 2024-03-29, with Batt "
                 "Voltage between 113 and 151, one PwrCurTargetState value and an Lvi_Flag of "
                 "0 on every row. A row records that the power manager logged that line at "
                 "that time. A row is reported only for a line that runs to a newline and "
                 "matches the whole of a shape named here. A line cut at the end of a block is "
                 "still reported if the next block begins with a newline and the shortened "
                 "text fits the shape; that was not seen on the tested unit. Times Found "
                 "counts how often the same line was found. In a free space file with its run "
                 "map present, a line is not read across two runs that were not neighbours on "
                 "the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 133 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 2148 rows",
        },
        "output_types": "standard",
        "artifact_icon": "battery",
    },
    "ford_sync4_phone_status": {
        "name": "Ford SYNC 4 - Bluetooth Phone Status In Log",
        "description": "Bluetooth phone status lines in the platform log: the phone status "
                       "line with its seven numbers, the Bluetooth radio status event line, "
                       "the connected phone notification and the number of phone devices, each "
                       "with its log time.",
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
                 "Rows come from four lines: the bluetooth.btbridge line 'PhnStatus: <n>, "
                 "BTStatus: <n>: NetworkStatus: <n>: MicStatus: <n>, BatteryLevel: <n>, "
                 "SignalStrength <n>, DefaultStatus:<n>' (Phone status), its "
                 "'bt_event_radio_status, state <n>' line (Radio status), and the "
                 "voice.dialog.phone.initiator lines 'BT notification for connected phone: "
                 "<word>' and 'Number Of Phone Devices = <n>'. Values are as stored and "
                 "nothing available here documents the numbers. The logical zip gave 59 rows; "
                 "the raw image gave 221 from 2023-07-18 to 2024-03-29: phone status 136 with "
                 "four distinct sets of values, radio status 52, connected phone notification "
                 "17, every one DISCONNECTED, and number of phone devices 16, every one 0. No "
                 "reported line names a phone. A row records that the module logged that line. "
                 "It does not establish that a phone was or was not in the vehicle. A row is "
                 "reported only for a line that runs to a newline and matches the whole of a "
                 "shape named here. A line cut at the end of a block is still reported if the "
                 "next block begins with a newline and the shortened text fits the shape; that "
                 "was not seen on the tested unit. Times Found counts how often the same line "
                 "was found. In a free space file with its run map present, a line is not read "
                 "across two runs that were not neighbours on the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 59 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 221 rows",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "ford_sync4_sirius_channel": {
        "name": "Ford SYNC 4 - SiriusXM Channel Lines In Log",
        "description": "SiriusXM lines in the platform log that name a channel: the current "
                       "channel line and the connectivity banner line with its chn# value, "
                       "each with its log time.",
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
                 "Rows come from two lines of the Sirius_Emma_Audio_Svc components: the "
                 "SXMAPIData_CCRI line 'Current channel : <text>', and the first line of the "
                 "ConnectivityBanner message, from 'ipAvailable: <n>' to 'chn#: <n>'. That "
                 "line must end ', ch' or ', ch.' after the chn# value: the message is wrapped "
                 "across log lines, and a banner line that wraps a letter or two later is not "
                 "reported (23 of 621 banner lines in the tested unit's free space). Values "
                 "are as stored. The live log files of the tested unit hold neither line, so "
                 "the logical zip gave no rows; the raw image gave 1,070 from 2023-12-06 to "
                 "2024-03-27: current channel 453, with five distinct channel texts each "
                 "followed by the words BAD PAUSE POINT, and connectivity banner 617. What "
                 "those words and the banner's numbers mean is not documented here. A row "
                 "records that the service logged that channel at that time. It does not "
                 "establish who was listening. A row is reported only for a line that runs to "
                 "a newline and matches the whole of a shape named here. A line cut at the end "
                 "of a block is still reported if the next block begins with a newline and the "
                 "shortened text fits the shape; that was not seen on the tested unit. Times "
                 "Found counts how often the same line was found. In a free space file with "
                 "its run map present, a line is not read across two runs that were not "
                 "neighbours on the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows: not in the live log files",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 1070 rows",
        },
        "output_types": "standard",
        "artifact_icon": "radio",
    },
    "ford_sync4_network_lines": {
        "name": "Ford SYNC 4 - Network Lines In Log",
        "description": "Network lines in the platform log: the wlan.dcs lines that state an "
                       "interface name and a MAC address, and the network up and down lines "
                       "with the IP address they state, each with its log time.",
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
                 "Rows come from two lines: the wlan.dcs line 'intf = <interface> has mac = "
                 "<address>' (Interface address), and the voice.utils.media.playerimpl line "
                 "'onNetworkStatusChanged, Player(<name>): Network update (UP IP: <address>)' "
                 "or '(DOWN IP: )' (Network update). Values are as stored. The logical zip "
                 "gave 55 rows; the raw image gave 127 from 2023-07-18 to 2024-03-29: "
                 "interface address 28, with two distinct interface and address pairs, and "
                 "network update 99. Which interface or network the address on an UP line "
                 "belongs to is not established here. A row is reported only for a line that "
                 "runs to a newline and matches the whole of a shape named here. A line cut at "
                 "the end of a block is still reported if the next block begins with a newline "
                 "and the shortened text fits the shape; that was not seen on the tested unit. "
                 "Times Found counts how often the same line was found. In a free space file "
                 "with its run map present, a line is not read across two runs that were not "
                 "neighbours on the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 55 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 127 rows",
        },
        "output_types": "standard",
        "artifact_icon": "globe",
    },
    "ford_sync4_update_packages": {
        "name": "Ford SYNC 4 - Package Transfers In Log",
        "description": "Packages named in three lines of the platform log's cpm component, one "
                       "row per package id, with the first and last log time, the total bytes "
                       "and highest percentage of its transfer progress lines, the states "
                       "logged and the number of checksum verified lines.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
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
                 "Rows come from three lines of the cpm component (matched as any component "
                 "whose name starts with cpm; only cpm exists on the tested unit), each ending "
                 "with a source position in brackets: 'Transfer PROGRESS. pkg=<id>, <n>% (<n> "
                 "B/<n> B) <n> Mbps, freeSpace=<n> MB, progressTypeWord=<word>.', which also "
                 "occurs with no percentage and '(<n> B/-)'; 'Message sent to listener. "
                 "pkg=<id>, topic=STATE, state=<word>.'; and 'VBF file checksum verified. "
                 "pkg=<id>.'. Lines are folded on the package id, one row per id, with the "
                 "first and last log time of its lines. Total Bytes is the second byte count "
                 "of its last progress line that states one, as stored with its commas; "
                 "Highest Percent is the largest percentage among its progress lines, read as "
                 "a number; Progress Lines counts both shapes; States lists the state words in "
                 "log time order, each once. Only a line that runs to a newline and matches "
                 "the whole of one of those shapes is counted. The live log files of the "
                 "tested unit hold no such line, so the logical zip gave no rows; the raw "
                 "image gave 20 rows, 2 with a first log time on 2023-07-18 and 18 on "
                 "2023-12-06. Every package id was six characters. 19 packages had progress "
                 "lines, 11 of them with a percentage and a total, 10 reaching 100 percent; 16 "
                 "showed the states STARTED, COMPLETED, CLOSED, 2 COMPLETED, CLOSED, 1 "
                 "COMPLETED and 1 none; 18 had a checksum verified line. The progress lines "
                 "carry the word update as their progressTypeWord. Nothing available here "
                 "documents what a package id identifies or what the states mean, so none is "
                 "translated. A row records that the cpm component logged those lines for that "
                 "id. It does not establish what was installed.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 0 rows: not in the live log files",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 20 rows",
        },
        "output_types": "standard",
        "artifact_icon": "download",
    },
    "ford_sync4_profile_lines": {
        "name": "Ford SYNC 4 - Personal Profile Lines In Log",
        "description": "Personal profile lines in the platform log, one row for each run of "
                       "lines that state the same values, with the first and last log time of "
                       "the run and the number of lines.",
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
                 "Rows come from three PASA_HMI_IF.Cluster lines: 'Personal profile id "
                 "received from BCM : <n> <word> received', 'Personal profile selected from "
                 "BCM. Profile Id: <n> key associated: <n>' and 'Notification for switch "
                 "profile completed from NPP. Profile Id = <n>', which the log writes with two "
                 "spaces before the equals sign. The lines of one kind are taken in log order "
                 "and a new row starts when the values change, so a row is a run of lines that "
                 "state the same values, with its first and last log time and the number of "
                 "lines. On the tested unit each kind stated one set of values throughout, so "
                 "each gave one row and the split into runs was not exercised: the logical zip "
                 "gave 3 rows from 671 lines, and the raw image 3 rows from 8,992 lines "
                 "(4,493, 4,489 and 10) from 2023-07-18 to 2024-03-29. What the profile ids "
                 "stand for is not documented here. A row records that the module logged those "
                 "values. It does not establish who was driving. A row is reported only for a "
                 "line that runs to a newline and matches the whole of a shape named here. A "
                 "line cut at the end of a block is still reported if the next block begins "
                 "with a newline and the shortened text fits the shape; that was not seen on "
                 "the tested unit. In a free space file with its run map present, a line is "
                 "not read across two runs that were not neighbours on the disk.",
        "paths": (
            '*/rwdata/logs/*fdplog*.txt*',
            '*.unallocated.bin',
            '*.unallocated.tsv',
            '*/DiskImages/mmcblk0.img',
        ),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 3 rows",
            "ford_syncg4": "Ford Sync 4, acquisition folder with the raw image | 3 rows",
        },
        "output_types": "standard",
        "artifact_icon": "user",
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
_TRIMBLE_IN = re.compile(r'^Trimble Input lat=(-?[\d.]+), lon=(-?[\d.]+), alt=(-?[\d.]+)')
_RAW_GPS = re.compile(r'^Raw GPS: latitude= (-?[\d.]+), longitude= (-?[\d.]+)$')
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
    ('nav.service', re.compile(r'Received new tire pressures: (.*)$'), 'Tire pressures'),
    ('AppLinkService.ZONE_23',
     re.compile(r'"method":"UI\.OnDriverDistraction","params":\{"state":"(\w+)"\}\}\]$'),
     'Driver distraction state'),
    ('AppLinkService.ZONE_23',
     re.compile(r'"method":"VehicleInfo\.OnVehicleData","params":\{"odometer":(\d+)\}\}\]$'),
     'Odometer in vehicle data notification'),
)
# The signals whose line is nothing but 'name = number' values.
_PAIR_SIGNALS = ('Door status', 'Gear position', 'Odometer value', 'Tire pressures')
# One value of a door, gear or odometer line, up to the separator that follows it.
_PAIR = re.compile(r'([A-Za-z][\w ]*? = \d+)(?=\s*,)')
# The values at the start of a cut line, each with its separator.
_LEADING = re.compile(r'(?:[A-Za-z][\w ]*? = \d+\s*,\s*)+')
# A whole door, gear or odometer line: nothing but such values.
_PAIRS = re.compile(r'[A-Za-z][\w ]*? = \d+(?:\s*,\s*[A-Za-z][\w ]*? = \d+)*')
# The other artifacts: (component prefix, pattern, what the row says). Each pattern runs to
# the end of the line, and only a line that ran to a newline is reported.
_POWER = (
    ('PowerManager.', re.compile(r'=event (\w+), EventValue = (\d+)$'),
     lambda m: (m.group(1), m.group(2))),
    ('PowerManager.', re.compile(r'=CAN event: ([a-z ]+)$'),
     lambda m: ('CAN event', m.group(1))),
    ('PowerManager.', re.compile(r'=BodyInfo_HS\d\.(Ignition_Status)=(\d+)$'),
     lambda m: (m.group(1), m.group(2))),
    ('PowerManager.', re.compile(r'=(Remote_Start_Status) is (\w+)$'),
     lambda m: (m.group(1), m.group(2))),
)
_BATTERY = (
    ('PowerManager.', re.compile(r'=Batt Voltage = (\d+), PwrCurTargetState = (\d+), '
                                 r'Lvi_Flag =(\d+)$'),
     lambda m: (m.group(1), m.group(2), m.group(3))),
)
_PHONE = (
    ('bluetooth.btbridge', re.compile(r'(PhnStatus: \d+, BTStatus: \d+: NetworkStatus: \d+: '
                                      r'MicStatus: \d+, BatteryLevel: \d+, '
                                      r'SignalStrength \d+, DefaultStatus:\d+)$'),
     lambda m: ('Phone status', m.group(1))),
    ('bluetooth.btbridge', re.compile(r'bt_event_radio_status, (state \d+)$'),
     lambda m: ('Radio status', m.group(1))),
    ('voice.dialog.phone.initiator',
     re.compile(r'^BT notification for connected phone: (\w+)$'),
     lambda m: ('Connected phone notification', m.group(1))),
    ('voice.dialog.phone.initiator', re.compile(r'^Number Of Phone Devices = (\d+)$'),
     lambda m: ('Number of phone devices', m.group(1))),
)
_SIRIUS = (
    ('Sirius_Emma_Audio_Svc.', re.compile(r'\[SXMAPIData_CCRI\]\S+\|Current channel\s+: '
                                          r'(\S+)((?: [\w ]+)?)$'),
     lambda m: ('Current channel', (m.group(1) + m.group(2)).strip())),
    ('Sirius_Emma_Audio_Svc.', re.compile(r'\[ConnectivityBanner\]\S+\|(ipAvailable: \d+, '
                                          r'satAvailable: \d+, [\w ,:#]*chn#: \d+), ch\.?$'),
     lambda m: ('Connectivity banner', m.group(1))),
)
_NETWORK = (
    ('wlan.dcs', re.compile(r'^intf = (\S+ has mac = [0-9a-fA-F:]{17})$'),
     lambda m: ('Interface address', m.group(1))),
    ('voice.utils.media.playerimpl',
     re.compile(r'onNetworkStatusChanged, (Player\(\w*\)): Network update '
                r'\(((?:UP|DOWN) IP: [\d.]*)\)$'),
     lambda m: ('Network update', m.group(1) + ' ' + m.group(2))),
)
_PROFILE = (
    ('PASA_HMI_IF.Cluster',
     re.compile(r'=Personal profile id received from BCM : (\d+ \w+) received$'),
     lambda m: ('Profile id received from BCM', m.group(1))),
    ('PASA_HMI_IF.Cluster',
     re.compile(r'=Personal profile selected from BCM\. (Profile Id: \d+ key associated: '
                r'\d+)$'),
     lambda m: ('Profile selected from BCM', m.group(1))),
    ('PASA_HMI_IF.Cluster',
     re.compile(r'=Notification for switch profile completed from NPP\. (Profile Id  = '
                r'\d+)$'),
     lambda m: ('Switch profile completed', m.group(1))),
)
# The package manager's lines end with the source position in brackets.
_UPDATES = (
    # with a percentage and a total, or with neither: '(<n> B/-)'
    ('cpm', re.compile(r'^Transfer PROGRESS\. pkg=(\w+), +(?:([\d.]+)% )?\([\d,]+ B/'
                       r'(?:([\d,]+) B|-)\) [\d.]+ Mbps, freeSpace=[\d,]+ MB, '
                       r'progressTypeWord=\w+\. \[[\w.]+:\d+:\w+\]$'),
     lambda m: (m.group(1), 'progress', (m.group(2), m.group(3)))),
    ('cpm', re.compile(r'^Message sent to listener\. pkg=(\w+), topic=STATE, state=(\w+)\. '
                       r'\[[\w.]+:\d+:\w+\]$'),
     lambda m: (m.group(1), 'state', m.group(2))),
    ('cpm', re.compile(r'^VBF file checksum verified\. pkg=(\w+)\. \[[\w.]+:\d+:\w+\]$'),
     lambda m: (m.group(1), 'verified', '')),
)
_RULES = _POWER + _BATTERY + _PHONE + _SIRIUS + _NETWORK + _PROFILE + _UPDATES
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
        return text.startswith(('Trimble Output', 'UbloxReader: lat', 'Trimble Input',
                                'Raw GPS: latitude'))
    if component == 'CM':
        return ' ssid = ' in text
    if component == 'evChargeSettings':
        return 'ChargeLocationMsg' in text
    if component == 'vendor.garmin':
        return 'hmi.analytics' in text
    if any(component == name and pattern.search(text) for name, pattern, _ in _SIGNALS):
        return True
    return any(component.startswith(prefix) and pattern.search(text)
               for prefix, pattern, _ in _RULES)


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
    """(match, text bytes, whole) for each line in each stretch.

    A block can end in the middle of a line. In an image the next block then starts
    another line with no newline between the two, and the unfinished line's text would
    run on into it. The text is cut where a new line starts, and the search goes on
    from there, so the second line is found as well.

    'whole' is true when the text ran to a newline. A line that stops any other way (the
    stretch ends, another line starts, or bytes that are not log text follow) is cut, and
    its last value may be cut with it.
    """
    for start, end in runs:
        position = start
        while position < end:
            match = _LINE.search(mapped, position, end)
            if match is None:
                break
            text = match.group(10)
            inner = _LINE_START.search(text)
            whole = not inner and match.end() < end \
                and mapped[match.end():match.end() + 1] == b'\n'
            if inner:
                text = text[:inner.start()]
                position = match.start(10) + inner.start()
            else:
                position = max(match.end(), match.start() + 1)
            yield match, text, whole


def _scan(path):
    """(log time, time text, component, sequence id, text, whole) for each kept line of one
    input.

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
        for match, raw_text, whole in _matches(mapped, _runs(path, size)):
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
            yield stamp, exact, component, int(match.group(9)), text, whole
    finally:
        mapped.close()
        handle.close()


def _log_lines(context):
    """Kept lines of every matched input, each once, oldest first.

    Returns (lines, source paths). A line is (log time, component, text, found in, times
    found, sequence id, whole); 'found in' names the kinds of input that held it, and
    'whole' is true when any copy of it ran to a newline.
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
        for stamp, exact, component, sequence, text, whole in _scan(path):
            found = True
            entry = merged.setdefault((exact, component, sequence, text),
                                      [stamp, set(), 0, False])
            entry[1].add(kind)
            entry[2] += 1
            entry[3] = entry[3] or whole
        if found:
            used.append(path)
        if kind != _LOG_FILE:
            logfunc(f'Ford SYNC 4 platform log: read {os.path.basename(path)} as '
                    f'{kind.lower()}')
    lines = [(entry[0], component, text, ', '.join(sorted(entry[1])), entry[2], sequence,
              entry[3])
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
    for stamp, component, text, where, _times, _sequence, whole in lines:
        # the longitude can be the last value of the line, so a cut line can hold part of one
        if component != 'evChargeSettings' or not whole:
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
    for stamp, component, text, where, _times, _sequence, _whole in lines:
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
    for stamp, component, text, where, times, _sequence, whole in lines:
        if component != 'lbs':
            continue
        trimble = _TRIMBLE.match(text)
        ublox = None if trimble else _UBLOX.match(text)
        if trimble:
            data_list.append((stamp, _number(trimble.group(2)), _number(trimble.group(3)),
                              'Trimble Output', trimble.group(1),
                              trimble.group(4) if whole else '', '', where, times))
        elif ublox:
            data_list.append((stamp, _number(ublox.group(1)), _number(ublox.group(2)),
                              'UbloxReader', '', '', ublox.group(3) if whole else '', where,
                              times))
        else:
            given = _TRIMBLE_IN.match(text)
            raw = _RAW_GPS.match(text)
            if given:
                data_list.append((stamp, _number(given.group(1)), _number(given.group(2)),
                                  'Trimble Input', '', given.group(3) if whole else '', '',
                                  where, times))
            elif raw and whole:
                # the longitude is the last value of the line
                data_list.append((stamp, _number(raw.group(1)), _number(raw.group(2)),
                                  'Raw GPS', '', '', '', where, times))

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Line Kind',
                    'Result (as stored)', 'Altitude (as stored)', 'Heading (as stored)',
                    'Found In', 'Times Found')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_wifi_access_points(context):
    lines, sources = _log_lines(context)
    found = {}
    for stamp, component, text, where, _times, _sequence, whole in lines:
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
        if whole:
            # a cut line can end inside the channel number
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
    for stamp, component, text, where, times, _sequence, whole in lines:
        for name, pattern, label in _SIGNALS:
            if component != name:
                continue
            match = pattern.search(text)
            if match:
                values = match.group(1).strip()
                if label in _PAIR_SIGNALS and not (whole and _PAIRS.fullmatch(values)):
                    # A cut line is followed by whatever the next block holds, which can
                    # be other text with its own newline. Only the 'name = number' pairs
                    # that came before the cut are kept.
                    whole = False
                    leading = _LEADING.match(values)
                    values = ', '.join(_PAIR.findall(leading.group(0))) if leading else ''
                if values:
                    data_list.append((stamp, label, values, 'Yes' if whole else 'No', where,
                                      times))
                break

    data_headers = (('Log Time', 'datetime'), 'Signal', 'Values (as stored)',
                    'Whole Line', 'Found In', 'Times Found')
    return data_headers, data_list, '\n'.join(sources)


def _rule_rows(context, rules):
    """(log time, values the rule gives, found in, times found) for each whole line a rule
    matches, oldest first, and the source paths."""
    lines, sources = _log_lines(context)
    rows = []
    for stamp, component, text, where, times, _sequence, whole in lines:
        if not whole:
            continue
        for prefix, pattern, values in rules:
            match = pattern.search(text) if component.startswith(prefix) else None
            if match:
                rows.append((stamp, values(match), where, times))
                break
    return rows, sources


def _kind_and_values(context, rules):
    rows, sources = _rule_rows(context, rules)
    data_list = [(stamp, kind, values, where, times)
                 for stamp, (kind, values), where, times in rows]
    data_headers = (('Log Time', 'datetime'), 'Line Kind', 'Values (as stored)', 'Found In',
                    'Times Found')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_power_events(context):
    rows, sources = _rule_rows(context, _POWER)
    data_list = [(stamp, event, value, where, times)
                 for stamp, (event, value), where, times in rows]
    data_headers = (('Log Time', 'datetime'), 'Event', 'Value (as stored)', 'Found In',
                    'Times Found')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_battery_voltage(context):
    rows, sources = _rule_rows(context, _BATTERY)
    data_list = [(stamp, voltage, state, flag, where, times)
                 for stamp, (voltage, state, flag), where, times in rows]
    data_headers = (('Log Time', 'datetime'), 'Batt Voltage (as stored)',
                    'PwrCurTargetState (as stored)', 'Lvi_Flag (as stored)', 'Found In',
                    'Times Found')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_phone_status(context):
    return _kind_and_values(context, _PHONE)


@artifact_processor
def ford_sync4_sirius_channel(context):
    return _kind_and_values(context, _SIRIUS)


@artifact_processor
def ford_sync4_network_lines(context):
    return _kind_and_values(context, _NETWORK)


@artifact_processor
def ford_sync4_profile_lines(context):
    rows, sources = _rule_rows(context, _PROFILE)
    runs = {}
    data_list = []
    for stamp, (kind, values), where, _times in rows:
        run = runs.get(kind)
        if run is None or run[3] != values:
            # the values changed for this kind of line: a new run starts
            run = runs[kind] = [stamp, stamp, kind, values, 0, set()]
            data_list.append(run)
        if stamp:
            run[0] = run[0] or stamp
            run[1] = stamp
        run[4] += 1
        run[5].update(where.split(', '))
    data_list = [(first, last, kind, values, count, _found_in(kinds))
                 for first, last, kind, values, count, kinds in data_list]
    data_headers = (('First Log Time', 'datetime'), ('Last Log Time', 'datetime'),
                    'Line Kind', 'Values (as stored)', 'Lines', 'Found In')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_update_packages(context):
    rows, sources = _rule_rows(context, _UPDATES)
    packages = {}
    for stamp, (package, kind, value), where, _times in rows:
        entry = packages.setdefault(package, ['', '', '', 0.0, 0, [], 0, 0, set(), False])
        if stamp:
            entry[0] = min(entry[0], stamp) if entry[0] else stamp
            entry[1] = max(entry[1], stamp)
        if kind == 'progress':
            percent, total = value
            if total:
                entry[2] = total
            if percent:
                entry[3] = max(entry[3], float(percent))
                entry[9] = True
            entry[4] += 1
        elif kind == 'state':
            if value not in entry[5]:
                entry[5].append(value)
            entry[6] += 1
        else:
            entry[7] += 1
        entry[8].update(where.split(', '))
    data_list = [(first, last, package, total, highest if has_percent else '', progress,
                  ', '.join(states), state_lines, verified, _found_in(kinds))
                 for package, (first, last, total, highest, progress, states, state_lines,
                               verified, kinds, has_percent)
                 in sorted(packages.items(), key=lambda item: (item[1][0], item[0]))]
    data_headers = (('First Log Time', 'datetime'), ('Last Log Time', 'datetime'), 'Package',
                    'Total Bytes (as stored)', 'Highest Percent', 'Progress Lines',
                    'States (as stored)', 'State Lines', 'Checksum Verified Lines', 'Found In')
    return data_headers, data_list, '\n'.join(sources)

