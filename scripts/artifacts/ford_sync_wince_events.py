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
    "ford_sync_wince_log_phone_lines": {
        "name": "Ford SYNC WinCE - Phone Connection Lines In Log",
        "description": "Lines of the module's log that name a phone connection attempt, a "
                       "connected HFP port or a disconnected one, in the log's own terms, read "
                       "from the log files and the raw partition image, each with its tick "
                       "count, a clock derived from the nearest line that states a date and "
                       "time, and where in the image it was found.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt, the log text beside a crash dump and "
                 "DiskImages/partition<n>.img, read the way the Log Events artifact reads "
                 "them. Three lines are reported. 'PhoneCore: Connecting to phone: [<name>] "
                 "(0x<address>). Attempt = <n>.' is a Connection Attempt: Device Name is the "
                 "name in brackets, Value the address shown in lower case with colons and "
                 "Attempt the number on the line. Earlier Gen1 versions write it as 'CBTPhone: "
                 "Connecting to phone: [<name>] (0x<address>)' with no attempt number, and "
                 "Attempt is then empty, as it is on one line of the 2014 Edge that is cut "
                 "short. 'Phone::OnPhoneHFPPortConnected: Last connected phone BT_ADDr=' is "
                 "Connected: Value is the eight hexadecimal digits the line holds after a "
                 "two-character prefix, in lower case, and on the seven tested lines they "
                 "equalled the last eight digits of an address in a Connection Attempt line of "
                 "the same unit. 'Phone::OnPhoneHFPPortDisconnected (<n>)' is Disconnected: "
                 "Value is the number in parentheses as stored, 131073 on all 22 tested lines, "
                 "and the line names no device. Tested on ten units from their acquisition "
                 "folders, eight SYNC Gen1 and two SYNC Gen2. Nine gave rows, 425 in all: six "
                 "earlier Gen1 units 81 attempts between them, none with an attempt number, "
                 "the Gen1 version 5 unit (2019 Ford Fusion) 86 attempts, the 2014 Ford Edge "
                 "SEL 185 attempts and 2 disconnects, and the 2011 Ford Explorer XLT 44 "
                 "attempts, 7 connected lines and 20 disconnects. One Gen1 unit held none of "
                 "these lines. An attempt is the module trying to connect to a paired phone. "
                 "It does so whether or not the phone answers: on the Edge, lines saying the "
                 "attempt hit a timeout stood in the same log. It does not establish that the "
                 "phone connected. No reported line carries a date. Derived Clock, Nearest "
                 "Clock Line, Clock Line Kind, Seconds From Clock Line and Clock Bias are "
                 "worked out as in the Log Events artifact, whose notes give the checks behind "
                 "them; 345 of the 425 rows have a derived clock, and on the Gen1 units that "
                 "clock is in 2003, the unit's own clock and not a calendar date to rely on. A "
                 "line found in a log file and again in the partition image is one row, with "
                 "Times Found, and the row keeps the reading that has a clock when only one "
                 "does. Where Found is as in the Log Events artifact: on the two Gen2 units "
                 "184 rows sat only in free clusters, 56 only in allocated clusters in no "
                 "listed file and 18 in a listed file. The image holds blocks of the log the "
                 "file system has released, so the rows are what survived, not a full history. "
                 "Other lines of the same connection code, such as the timeout line, are not "
                 "reported. A row records that the module logged the line. It does not "
                 "establish who carried the phone.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 9 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 4 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 20 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 38 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 0 rows, "
                             "none of these lines in the log files or the partition image",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 86 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 187 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 71 "
                             "rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 9 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "link",
    },
    "ford_sync_wince_log_paired_device_lines": {
        "name": "Ford SYNC WinCE - Paired Device Lines In Log",
        "description": "Entries of the paired device list the module writes into its log, read "
                       "from the log files and the raw partition image: one row per distinct "
                       "entry, with the device name, device address, device number, the active "
                       "and primary values and pair order on the line, how many times its line "
                       "was found across the sources and where in the image.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From lines of the form 'device: <n>. [<name>] [0x0000<address>], active = "
                 "<a>, primary = <p>, pairorder = <o>' in Windows/LogFiles/MsgLog<n>.txt, the "
                 "log text beside a crash dump and DiskImages/partition<n>.img, read the way "
                 "the Log Events artifact reads them. The log writes the device list again and "
                 "again, so lines with the same name, address and four numbers are one row. "
                 "Times Found is how many times the line was found across every source, and a "
                 "line in an extracted file is counted again where the image holds it. Device "
                 "Address is the 12 hexadecimal digits in the second bracket, shown in lower "
                 "case with colons. Tested on ten units from their acquisition folders, eight "
                 "SYNC Gen1 and two SYNC Gen2: 1,803 line readings (937 in the partition "
                 "images, 866 in the extracted log files and crash dump text, a line present "
                 "in both counted in both) gave 39 rows holding 33 device addresses, counted "
                 "per unit. On the eight Gen1 units the addresses were the same ones the "
                 "Paired Devices In Log artifact reads from the log files. The 2014 Edge's two "
                 "extracted log files hold no such line and the Explorer's extracted set has "
                 "no log file, so their rows came from the partition image alone: 2 rows for 1 "
                 "address on the 2014 Ford Edge SEL and 7 rows for 6 addresses on the 2011 "
                 "Ford Explorer XLT, all in free clusters or in allocated clusters in no "
                 "listed file. An independent parse of the Explorer listed 7 Bluetooth "
                 "addresses, and the 6 here are among them. A device has more than one row "
                 "when its numbers, or its name, differ between lines; on the tested units "
                 "only the numbers differed. Active and Primary are shown as stored and what "
                 "each value stands for is not documented here; Pair Order is the number the "
                 "line calls pairorder. No such line carries a date. Earliest Derived Clock "
                 "and Latest Derived Clock are the lowest and highest clock derived for the "
                 "row's lines, worked out as in the Log Events artifact, whose notes give the "
                 "checks behind it; 26 of the 39 rows have one, in 2003 on the Gen1 units, "
                 "which is the unit's own clock and not a calendar date to rely on, and in "
                 "2020 on 2 rows of the Explorer. Where Found is as in the Log Events artifact "
                 "and lists every place the row's lines sat. Source File is the first matched "
                 "file, in path order, that held the row; on the tested units that is the "
                 "partition image for every row, and Where Found says where else the line sat. "
                 "The text after pairorder on the line is not surfaced. A row records that the "
                 "module listed the device as paired in its log. It does not establish when "
                 "the device was paired or who carried it.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 1 row",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 5 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 2 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 4 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 4 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 3 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 2 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 7 rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 4 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 7 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "ford_sync_wince_log_device_activity_lines": {
        "name": "Ford SYNC WinCE - Device Activity Lines In Log",
        "description": "Lines of the module's log that record a Bluetooth device being "
                       "activated or deactivated, a call list file being saved for a device, "
                       "and the emergency assist code logging a phone connect or disconnect "
                       "status event, read from the log files and the raw partition image, "
                       "each with its tick count, a derived clock and where in the image it "
                       "was found.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt, the log text beside a crash dump and "
                 "DiskImages/partition<n>.img, read the way the Log Events artifact reads "
                 "them. Five lines are reported. 'CBTPairSvc::ActivateBTDevice() : Device "
                 "<address>, 0x.., 0x..' is Device Activated and "
                 "'CBTPairSvc::DeActivateBTDevice() : Device <address>, 0x..' is Device "
                 "Deactivated: Device Address is the 12 hexadecimal digits on the line, "
                 "shown in lower case with colons, and Values After Address holds the one or"
                 " two hexadecimal values that follow it as stored, which nothing available "
                 "here documents. 'PhoneCore:CCallHistoryList: Saved to "
                 "[\\windows\\phonebook\\CH<address>.xml]' is Call List Saved, with the address"
                 " taken from the file name. 'EmergencyAssist::HandlePhoneStatusEvent "
                 "EVM_BTPHONE_CONNECT.' and the same with DISCONNECT are Assist Phone "
                 "Connect and Assist Phone Disconnect; those lines name no device. Tested on"
                 " ten units from their acquisition folders, eight SYNC Gen1 and two SYNC "
                 "Gen2. Eight gave rows, 837 in all: 373 activations, 366 deactivations, 49 "
                 "call list saves and, on the 2011 Ford Explorer XLT only, 10 assist "
                 "connects and 39 assist disconnects. Two Gen1 units held none of these "
                 "lines. The words activated and deactivated are the log's own; what the "
                 "module does at that point is not documented here, so a row does not by "
                 "itself establish that a call or a connection took place. A call list save "
                 "line records that the module logged saving the call list file for that "
                 "device at that point in the log. The call list document carries no date of"
                 " its own saving. No reported line carries a date. Derived Clock, Nearest "
                 "Clock Line, Clock Line Kind, Seconds From Clock Line and Clock Bias are "
                 "worked out as in the Log Events artifact, whose notes give the checks "
                 "behind them; 629 of the 837 rows have a derived clock, in 2003 on the Gen1"
                 " units, which is the unit's own clock and not a calendar date to rely on. "
                 "A line found in a log file and again in the partition image is one row, "
                 "with Times Found, and the row keeps the reading that has a clock when only"
                 " one does. Where Found is as in the Log Events artifact: on the two Gen2 "
                 "units 385 rows sat only in free clusters, 121 only in allocated clusters "
                 "in no listed file and 35 in a listed file. The image holds blocks of the "
                 "log the file system has released, so the rows are what survived, not a "
                 "full history. A row records that the module logged the line. It does not "
                 "establish who carried the device.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 20 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 12 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 3 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 0 rows, no"
                             " such line in the log files or the partition image",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 0 rows, no"
                             " such line in the log files or the partition image",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 243 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 372 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 169 "
                             "rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 16 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 2 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "ford_sync_wince_log_power_lines": {
        "name": "Ford SYNC WinCE - Power Lines In Log",
        "description": "Lines of the module's log that record a power state being started and, "
                       "on the tested SYNC Gen1 version 5 unit, a change in the system state "
                       "the log spells out in six named fields (sysRunSt, HmiSt, SysReady, "
                       "IgnSt, PwrMode and DrvDstr, as the log writes them), read from the log "
                       "files and the raw partition image, each with its tick count, a derived "
                       "clock and where in the image it was found.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt, the log text beside a crash dump and "
                 "DiskImages/partition<n>.img, read the way the Log Events artifact reads "
                 "them. 'PM: PlatformSetSystemPowerState( <name> ) started.' is Power State "
                 "Started, and State Or Change is the name on the line: waiton, waitsuspend, "
                 "suspend, displayonly, infotainment, reboot and vhm occurred on the tested "
                 "units. The names are the log's own and what each state does is not "
                 "documented here. Lines of the same call that give a number in place of a "
                 "name are not reported. 'SM: <name>CoreStateMachine::onEvent SystemState: "
                 "sysRunSt:<a>-><b> HmiSt: SysReady: IgnSt: PwrMode: DrvDstr:' is System State "
                 "Change, reported only when one or more of the six pairs differs, and State "
                 "Or Change then lists the pairs that differ, as written. Two state machines "
                 "write the line. A change is one row when the event, the change and the tick "
                 "are the same. On the tested unit no change was written by both machines at "
                 "the same tick. Tested on ten units from their acquisition folders, eight "
                 "SYNC Gen1 and two SYNC Gen2, which gave 2,282 rows: 1,073 power state starts "
                 "on all ten units and 1,209 system state changes, all on the Gen1 version 5 "
                 "unit (2019 Ford Fusion). Of those 1,209, 894 change only DrvDstr between 0 "
                 "and 1, 162 change only HmiSt, and 153 change IgnSt, PwrMode or sysRunSt, "
                 "such as IgnSt:Run->Off with PwrMode:Run->Access. What DrvDstr stands for is "
                 "not established here. No reported line carries a date. Derived Clock, "
                 "Nearest Clock Line, Clock Line Kind, Seconds From Clock Line and Clock Bias "
                 "are worked out as in the Log Events artifact, whose notes give the checks "
                 "behind them; 1,424 of the 2,282 rows have a derived clock, in 2003 on the "
                 "Gen1 units, which is the unit's own clock and not a calendar date to rely "
                 "on. A line found in a log file and again in the partition image is one row, "
                 "with Times Found, and the row keeps the reading that has a clock when only "
                 "one does. Where Found is as in the Log Events artifact. The image holds "
                 "blocks of the log the file system has released, so the rows are what "
                 "survived, not a full history. A row records that the module logged the line. "
                 "It does not establish who was in the vehicle.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 33 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 27 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 27 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 32 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 33 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 1352 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 404 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 320 "
                             "rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 21 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 33 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_sync_wince_log_clock_lines": {
        "name": "Ford SYNC WinCE - Clock Lines In Log",
        "description": "Lines of the module's log that state a date and time, one row per line: "
                       "the log save line and, on SYNC Gen2, the clock service line, read from "
                       "the log files and the raw partition image, with the tick count and where"
                       " in the image the line was found.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt, the log text beside a crash dump and "
                 "DiskImages/partition<n>.img, read the way the Log Events artifact reads "
                 "them. Two lines state a date and time: the log save line ('SYSHEALTH: start "
                 "saving retailmsg at', written month first) and, on Gen2, the clock service "
                 "line ('SyncClockSvc!MFDMessageThreadProc: (YMDhms)', written year first). "
                 "Clock On Line is the value the line states, written out with no offset "
                 "applied. These are the lines the Log Events artifact derives its clock from, "
                 "shown here as rows of their own because each one records that the module was "
                 "running and logging at that reading of its clock. Tested on ten units from "
                 "their acquisition folders, eight SYNC Gen1 and two SYNC Gen2, which gave "
                 "1,077 rows: 441 log save lines and 636 clock service lines. The eight Gen1 "
                 "units gave 123 rows, log save lines only, and every reading fell in 2003, so "
                 "on those units it is the unit's own clock and not a calendar date to rely "
                 "on. The 2014 Ford Edge SEL gave 589 rows with readings from 2010 to 2020 and "
                 "the 2011 Ford Explorer XLT 365 rows with readings from 2010 to 2033; a "
                 "reading outside the vehicle's life is the clock being unset or wrong, and "
                 "nothing here says which readings were right. The clock service line also has "
                 "a Bias line beside it, which the Log Events artifact shows and which is not "
                 "applied here. An independent parse of the two Gen2 units listed 414 and 239 "
                 "distinct time update times; all 407 and 229 clock service readings here are "
                 "among them. Its log save start times equal the reading a save line states on "
                 "22 of 182 and 15 of 136 distinct save readings here. For a further 102 and "
                 "74, a clock service reading among the 50 clock service lines either side in "
                 "the image, plus the difference in ticks read as milliseconds, gives that "
                 "parse's time to within a second. A control that shifted that parse's times "
                 "by 37 seconds matched 9 and 13 the same way, so a few of these may be "
                 "chance. That fits that parse working its time out from a clock service line "
                 "and the tick count, where Clock On Line shows what the save line states, and "
                 "the two clocks did not always agree. The remaining 58 and 47 were not "
                 "reproduced either way. A line found in more than one place is one row, with "
                 "Times Found. Where Found is as in the Log Events artifact; the Gen1 "
                 "partition images are FAT with 2,048-byte sectors, which the reader does not "
                 "read, so their rows read 'file system not read' beside 'extracted file' when "
                 "a log file held the line too. On the Gen1 units 14 of the 123 rows came from "
                 "the partition image alone. The Log Save Clock Readings artifact lists the "
                 "save lines of the log files with their line numbers; this one adds the "
                 "partition image and the clock service line. A row records what the module's "
                 "clock read when it wrote the line.",
        "paths": (
            '*/Windows/LogFiles/MsgLog*.txt*',
            '*/Windows/DumpFiles/*.RTL',
            '*/DiskImages/partition*.img',
        ),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, acquisition folder | 12 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, acquisition folder | 8 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, acquisition folder | 6 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, acquisition folder | 9 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, acquisition folder | 7 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, acquisition folder | 64 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, acquisition folder | 589 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, acquisition folder | 365 "
                             "rows",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, acquisition folder | 11 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, acquisition folder | 6 rows",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
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
_CLOCK_ALTERNATIVES = (
    rb'SYSHEALTH: start saving retailmsg at (?P<save>\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)'
    rb'|SyncClockSvc!MFDMessageThreadProc: \(YMDhms\) '
    rb'(?P<clock>\d{1,4}/\d{1,2}/\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})'
    rb'|SyncClockSvc!MFDMessageThreadProc:  Bias = (?P<bias>-?\d+) ')
_PHONE = re.compile(
    rb'(?P<tick>\d{1,10}) +(?:'
    rb'(?:PhoneCore|CBTPhone): Connecting to phone: \[(?P<name>[^\r\n\]]{0,80})\] '
    rb'\(0x(?P<address>[0-9A-Fa-f]{1,12})\)(?:\. Attempt = (?P<attempt>\d+)\.)?'
    rb'|Phone::OnPhoneHFPPortConnected: Last connected phone BT_ADDr=\dx'
    rb'(?P<connected>[0-9A-Fa-f]{8}) '
    rb'|Phone::OnPhoneHFPPortDisconnected \((?P<disconnected>\d+)\)'
    rb'|' + _CLOCK_ALTERNATIVES + rb')')
_PAIRED = re.compile(
    rb'(?P<tick>\d{1,10}) +(?:'
    rb'\tdevice: (?P<index>\d+)\. \[(?P<name>[^\r\n]{0,80}?)\] '
    rb'\[0x0000(?P<address>[0-9A-Fa-f]{12})\], active = (?P<active>\d+), '
    rb'primary = (?P<primary>\d+), pairorder = (?P<order>\d+)'
    rb'|' + _CLOCK_ALTERNATIVES + rb')')
_ACTIVITY = re.compile(
    rb'(?P<tick>\d{1,10}) +(?:'
    rb'CBTPairSvc::(?P<act>Activate|DeActivate)BTDevice\(\) : Device '
    rb'(?P<address>[0-9A-Fa-f]{12}), (?P<rest>0x[0-9A-Fa-f]+(?:, 0x[0-9A-Fa-f]+)?)'
    rb'|EmergencyAssist::HandlePhoneStatusEvent EVM_BTPHONE_(?P<assist>CONNECT|DISCONNECT)\.'
    rb'|PhoneCore:CCallHistoryList: Saved to \[\\windows\\phonebook\\CH'
    rb'(?P<saved>[0-9A-Fa-f]{12})\.xml\]'
    rb'|' + _CLOCK_ALTERNATIVES + rb')')
_STATE_FIELDS = ('sysRunSt', 'HmiSt', 'SysReady', 'IgnSt', 'PwrMode', 'DrvDstr')
_POWER = re.compile(
    rb'(?P<tick>\d{1,10}) +(?:'
    rb'PM: PlatformSetSystemPowerState\( (?P<state>[A-Za-z]+) \) started\.'
    rb'|SM: \w{1,24}CoreStateMachine::onEvent SystemState: (?P<system>'
    rb'sysRunSt:\w+->\w+ HmiSt:\w+->\w+ SysReady:\w+->\w+ IgnSt:\w+->\w+ '
    rb'PwrMode:\w+->\w+ DrvDstr:\w+->\w+)'
    rb'|' + _CLOCK_ALTERNATIVES + rb')')
_CLOCK = re.compile(rb'(?P<tick>\d{1,10}) +(?:' + _CLOCK_ALTERNATIVES + rb')')
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


def _describe_phone(match):
    """(event, detail, value, second value) for a phone line; None for a clock line."""
    if match.group('address'):
        return ('Connection Attempt', match.group('name').decode('utf-8', 'replace'),
                _address(match.group('address').decode('ascii')),
                int(match.group('attempt')) if match.group('attempt') else '')
    if match.group('connected'):
        return 'Connected', '', match.group('connected').decode('ascii').lower(), ''
    if match.group('disconnected'):
        return 'Disconnected', '', int(match.group('disconnected')), ''
    return None


def _describe_paired(match):
    """(event, name, address, numbers) for a paired device line; None for a clock line."""
    if match.group('address'):
        return ('Paired Device', match.group('name').decode('utf-8', 'replace'),
                _address(match.group('address').decode('ascii')),
                (int(match.group('index')), int(match.group('active')),
                 int(match.group('primary')), int(match.group('order'))))
    return None


def _describe_activity(match):
    """(event, detail, address, values) for a device activity line; None for a clock line."""
    if match.group('act'):
        event = 'Device Activated' if match.group('act') == b'Activate' \
            else 'Device Deactivated'
        return (event, '', _address(match.group('address').decode('ascii')),
                match.group('rest').decode('ascii'))
    if match.group('assist'):
        event = 'Assist Phone Connect' if match.group('assist') == b'CONNECT' \
            else 'Assist Phone Disconnect'
        return event, '', '', ''
    if match.group('saved'):
        return 'Call List Saved', '', _address(match.group('saved').decode('ascii')), ''
    return None


def _describe_power(match):
    """(event, detail, '', '') for a power line; None for a clock line or no change."""
    if match.group('state'):
        return 'Power State Started', match.group('state').decode('ascii'), '', ''
    if match.group('system'):
        changed = []
        for pair in match.group('system').decode('ascii').split(' '):
            name, _colon, values = pair.partition(':')
            before, _arrow, after = values.partition('->')
            if name in _STATE_FIELDS and before != after:
                changed.append(pair)
        if changed:
            return 'System State Change', ' '.join(changed), '', ''
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


def _sessions(data, pattern=_EVENT):
    """Runs of matched lines that share one stretch of log and one boot.

    Two matched lines belong together only when every byte between them is log text and
    the tick count has not gone down, which is what a restart or an unrelated block
    looks like. Each run is a list of regex matches in written order.
    """
    run = []
    previous_end = None
    previous_tick = None
    for match in pattern.finditer(data):
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


def _events(data, pattern=_EVENT, describe=_describe):
    """Event rows of one source, each with the clock derived from the nearest clock line."""
    for run in _sessions(data, pattern):
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
            described = describe(match)
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


def _listed_event_lines(image, pattern=_EVENT, describe=_describe):
    """The text of every event line in the files an exFAT image lists."""
    lines = set()
    for content in image.listed_files():
        for match in pattern.finditer(content):
            if describe(match) is not None:
                lines.add(bytes(match.group(0)))
    return lines


def _clock_rows(data):
    """((clock, kind, tick), offset, line) for each line that states a date and time."""
    for match in _CLOCK.finditer(data):
        stated = _clock_line(match)
        if stated is None:
            continue
        yield ((stated[0].strftime('%Y-%m-%d %H:%M:%S'), stated[1],
                int(match.group('tick'))), match.start(), bytes(match.group(0)))


def _collect(context, label, find, listed_lines):
    """Rows of every source, folded: {row: [times found, offset, path, places]}."""
    rows = {}
    source_paths = []
    for file_found, data in _sources(context):
        hits = list(find(data))
        image = _ExfatImage(file_found) if _is_partition_image(file_found) else None
        listed = listed_lines(image) if image is not None and image.readable and hits \
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
        logfunc(f'Ford SYNC WinCE {label}: {len(hits)} lines in '
                f'{os.path.basename(file_found)}')
        if image is not None:
            image.close()
    return rows, source_paths


def _one_row_a_line(context, rows):
    """Report rows, one a log line, from what _collect gathered.

    One line can be found in a log file and again in the partition image, where the
    stretch around it can lack a clock line. Keep one row a line, the one with a clock.
    """
    lines = {}
    for row, (found, offset, path, places) in rows.items():
        key = row[1:6]
        if key not in lines:
            lines[key] = [row, found, offset, path, set(places)]
            continue
        kept = lines[key]
        kept[1] += found
        kept[4] |= places
        if not kept[0][0] and row[0]:
            kept[0], kept[2], kept[3] = row, offset, path
    data_list = [row + (found, _places(places), offset, context.get_relative_path(path))
                 for row, found, offset, path, places in lines.values()]
    data_list.sort(key=lambda row: (row[0] == '', row[0], row[5]))
    return data_list


@artifact_processor
def ford_sync_wince_log_device_activity_lines(context):
    rows, source_paths = _collect(
        context, 'log device activity lines',
        lambda data: _events(data, _ACTIVITY, _describe_activity),
        lambda image: _listed_event_lines(image, _ACTIVITY, _describe_activity))
    data_list = [(row[0], row[1]) + row[3:] for row in _one_row_a_line(context, rows)]

    data_headers = (('Derived Clock', 'datetime'), 'Event', 'Device Address',
                    'Values After Address (as stored)', 'Tick',
                    ('Nearest Clock Line', 'datetime'), 'Clock Line Kind',
                    'Seconds From Clock Line', 'Clock Bias (as stored)', 'Times Found',
                    'Where Found', 'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_power_lines(context):
    rows, source_paths = _collect(
        context, 'log power lines',
        lambda data: _events(data, _POWER, _describe_power),
        lambda image: _listed_event_lines(image, _POWER, _describe_power))
    data_list = [row[:3] + row[5:] for row in _one_row_a_line(context, rows)]

    data_headers = (('Derived Clock', 'datetime'), 'Event', 'State Or Change', 'Tick',
                    ('Nearest Clock Line', 'datetime'), 'Clock Line Kind',
                    'Seconds From Clock Line', 'Clock Bias (as stored)', 'Times Found',
                    'Where Found', 'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_phone_lines(context):
    rows, source_paths = _collect(
        context, 'log phone lines', lambda data: _events(data, _PHONE, _describe_phone),
        lambda image: _listed_event_lines(image, _PHONE, _describe_phone))
    data_list = _one_row_a_line(context, rows)

    data_headers = (('Derived Clock', 'datetime'), 'Event', 'Device Name',
                    'Value', 'Attempt', 'Tick',
                    ('Nearest Clock Line', 'datetime'), 'Clock Line Kind',
                    'Seconds From Clock Line', 'Clock Bias (as stored)',
                    'Times Found', 'Where Found', 'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_paired_device_lines(context):
    rows, source_paths = _collect(
        context, 'log paired device lines',
        lambda data: _events(data, _PAIRED, _describe_paired),
        lambda image: _listed_event_lines(image, _PAIRED, _describe_paired))
    # The log writes the device list again and again. One row a distinct entry, with how
    # many lines held it and the earliest and latest clock derived for them.
    devices = {}
    for row, (found, _offset, path, places) in rows.items():
        derived, _event, name, address, numbers = row[:5]
        key = (name, address) + numbers
        if key not in devices:
            devices[key] = [found, derived, derived, path, set(places)]
            continue
        kept = devices[key]
        kept[0] += found
        kept[4] |= places
        if derived:
            kept[1] = min(kept[1], derived) if kept[1] else derived
            kept[2] = max(kept[2], derived)
    data_list = [(first, last, name, address, index, active, primary, order, found,
                  _places(places), context.get_relative_path(path))
                 for (name, address, index, active, primary, order),
                 (found, first, last, path, places) in devices.items()]
    data_list.sort(key=lambda row: (row[3], row[4], row[0] == '', row[0]))

    data_headers = (('Earliest Derived Clock', 'datetime'), ('Latest Derived Clock', 'datetime'),
                    'Device Name', 'Device Address', 'Device Number', 'Active (as stored)',
                    'Primary (as stored)', 'Pair Order', 'Times Found', 'Where Found',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_clock_lines(context):
    def listed_lines(image):
        return {bytes(match.group(0)) for content in image.listed_files()
                for match in _CLOCK.finditer(content) if _clock_line(match) is not None}

    rows, source_paths = _collect(context, 'log clock lines', _clock_rows, listed_lines)
    data_list = [row + (found, _places(places), offset, context.get_relative_path(path))
                 for row, (found, offset, path, places) in rows.items()]
    data_list.sort(key=lambda row: (row[0], row[2]))

    data_headers = (('Clock On Line', 'datetime'), 'Clock Line Kind', 'Tick', 'Times Found',
                    'Where Found', 'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


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
