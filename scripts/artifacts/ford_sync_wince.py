"""Ford SYNC on Windows CE: the Accessory Protocol Interface Module, generations 1 and 2.

Named for the module and its platform, not a vehicle model: the same file layout was
found in Ford Edge, Escape and Fusion units across SYNC Gen1 versions 2 to 5, and the
call list and log files are also present on a SYNC Gen2 unit. The Gen1 units' own logs
name the kernel as Windows CE, and the Gen2 unit carries the same Windows directory
layout. The user data sits on one flash partition as small files keyed by the handset's
Bluetooth address:

    Windows/phonebook/CH<address>.xml      three call lists per handset (Gen1 and Gen2)
    Windows/phonebook/PB<address>.SYN      the downloaded phonebook, a binary list (Gen1)
    TextMsgApp/TextMessages_<address>      fixed-size UTF-16 message records (Gen1)
    MediaCache/Source_<n>.dat              one media source per slot (Gen1)
    Windows/LogFiles/MsgLog<n>.txt         the unit's rolling debug log (Gen1 and Gen2)
    Windows/DumpFiles/<dump>/<dump>.RTL    the log text saved beside a crash dump
    Windows/phonebook/persistentPhonebook_<address>.txt   one contact name a line

Every binary reader here checks the file's own framing (declared lengths, record
counts, record size) and gives the file up, with a log line, when it does not hold.
"""

import os
import re
import struct
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, device_info, logfunc

__artifacts_v2__ = {
    "ford_sync_wince_call_history": {
        "name": "Ford SYNC WinCE - Call History",
        "description": "Entries of the three call lists the module keeps for each handset, "
                       "with the name and number stored in each entry, its position in the "
                       "list, and the call time where the entry carries one.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/phonebook/CH<address>.xml, one file per handset. Tested on "
                 "eight SYNC Gen1 units: Ford Escape 2010 to 2014 (six units), Ford Edge 2013, "
                 "and Ford Fusion 2019, covering Gen1 versions 2, 3, 4 and 5 and read from the "
                 "file sets extracted from each unit's flash image. Each file holds three "
                 "CallHistory lists with type 0x10000, 0x20000 and 0x40000, shown as Call List "
                 "Type. Call List decodes them as Incoming, Outgoing and Missed. That mapping "
                 "was derived by comparison on one unit: an independent parse of the same file "
                 "labelled its 5, 7 and 22 entries, and each list matched one label entry for "
                 "entry. Any other type is left undecoded. Handset Address is the id attribute "
                 "of the file's Device element, shown with colons. Position In List is the "
                 "entry's order in the file; whether the first entry is the newest is not "
                 "established here. Call Time comes from the entry's time attribute, which "
                 "only the version 5 unit wrote (59 entries); on the other seven units the "
                 "Call Time column is empty because the entries carry no time. The attribute "
                 "has no time zone and is written out as if it were UTC with no offset "
                 "applied. An entry records that the module held this call list entry for the "
                 "handset. It does not establish who used the handset. A SYNC Gen2 unit (2014 "
                 "Ford Edge SEL) carried one CH file in the same format, with 68 entries and "
                 "no time attribute, and it is read the same way.",
        "paths": ('*/Windows/phonebook/CH*.xml*',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 27 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 34 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 161 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 214 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 299 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 59 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 68 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no CH file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 212 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 264 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "ford_sync_wince_phonebook": {
        "name": "Ford SYNC WinCE - Phonebook",
        "description": "Contacts in the phonebook files the module keeps for each handset, "
                       "with the name and the phone numbers stored for each contact.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/phonebook/PB<address>.SYN and, on one unit, a PB<address>.NEW "
                 "beside it. Tested on eight SYNC Gen1 units: Ford Escape 2010 to 2014 (six "
                 "units), Ford Edge 2013, and Ford Fusion 2019, covering Gen1 versions 2, 3, 4 "
                 "and 5 and read from the file sets extracted from each unit's flash image. "
                 "The file is a binary list: a total length, a four-byte signature, a contact "
                 "count, then for each contact a length-prefixed name and a counted list of "
                 "numbers, each with a two-byte type. All 21 phonebook files on the tested "
                 "units parsed to their exact end under that layout, and a file that does not "
                 "is logged and not read. Number Types is that two-byte value for each number, "
                 "in the same order as Phone Numbers; values 0 to 5 occur and nothing "
                 "available here documents them. Handset Address is the twelve hex digits in "
                 "the file name, shown with colons. What distinguishes a .NEW file from a .SYN "
                 "file is not established here; both are read and Source File says which. The "
                 "persistentPhonebook_<address>.txt files in the same folder are text lists "
                 "with one short entry per line and nothing linking a name to a number, and "
                 "are not read. A phonebook entry records that the module held the contact for "
                 "that handset. It does not establish that any number was dialled.",
        "paths": ('*/Windows/phonebook/PB*',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 21 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 932 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 191 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 80 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 1828 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 102 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "PB file in the extracted set",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no PB file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 478 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 175 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "ford_sync_wince_persistent_phonebook": {
        "name": "Ford SYNC WinCE - Persistent Phonebook Names",
        "description": "Contact names in the plain-text name list the module keeps for a "
                       "handset, one name a line, with the handset address from the file name.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/phonebook/persistentPhonebook_<address>.txt, a text file with "
                 "one name a line and no numbers. Tested on ten Ford SYNC units read from "
                 "their extracted file sets; four SYNC Gen1 units (Ford Escape 2011 to 2014) "
                 "held eight such files and gave 1,689 rows, and the other six had none. What "
                 "the module uses the list for is not established here. Each of the eight "
                 "handsets also has a binary phonebook file, read by the Phonebook artifact, "
                 "and 1,496 of the 1,689 names are in it for the same handset; the other 193 "
                 "are only here. Handset Address is the twelve hex digits in the file name, "
                 "shown with colons. Six files read as UTF-8 and two did not and were read as "
                 "Windows-1252, which is an assumption about those two; Text Read As says "
                 "which was used. A row records that the module listed the name for that "
                 "handset. It does not establish that the contact was called.",
        "paths": ('*/Windows/phonebook/persistentPhonebook_*',),
        "output_types": "standard",
        "artifact_icon": "book-open",
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "persistentPhonebook file in the extracted set",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 158 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "persistentPhonebook file in the extracted set",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 0 rows, no "
                             "persistentPhonebook file in the extracted set",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 924 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 0 rows, no "
                             "persistentPhonebook file in the extracted set",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "persistentPhonebook file in the extracted set",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no persistentPhonebook file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 432 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 175 rows",
        },
    },
    "ford_sync_wince_text_messages": {
        "name": "Ford SYNC WinCE - Text Messages",
        "description": "Text message records the module stored for each handset, with the "
                       "message time, the phone number, the name and the message text held in "
                       "each record.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From TextMsgApp/TextMessages_<address>, a file of fixed-size records with "
                 "UTF-16 text. Tested on eight SYNC Gen1 units: Ford Escape 2010 to 2014 (six "
                 "units), Ford Edge 2013, and Ford Fusion 2019, covering Gen1 versions 2, 3, 4 "
                 "and 5 and read from the file sets extracted from each unit's flash image. "
                 "Two record sizes occur: 988 bytes on versions 2 to 4 and 1072 bytes on the "
                 "version 5 unit. In both, the number starts the record, the name is at offset "
                 "0x202 and the text at 0x284, each ending at its first NUL, and a Windows "
                 "SYSTEMTIME follows the text. A file whose size is not a whole number of "
                 "records, or whose time fields are not valid, is logged and not read. Fifteen "
                 "of the 22 files on the tested units were empty; six held 5 records each, on "
                 "versions 2 and 3, and the version 5 file held 99. Message Time is that "
                 "SYSTEMTIME as stored, with no time zone, written out as if it were UTC. The "
                 "tested units held years from 2003 to 2034, so a reading on its own does not "
                 "establish when a message was sent. Whether a record is a received or a sent "
                 "message is not recorded in a field this artifact decodes. Flag is the "
                 "four-byte value after the time; 0, 1 and 2 occur and nothing available here "
                 "documents them. Handset Address is the twelve hex digits in the file name, "
                 "shown with colons. A record establishes that the module stored this text for "
                 "the handset. It does not establish who read or wrote it.",
        "paths": ('*/TextMsgApp/TextMessages_*',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 0 rows, every "
                             "TextMessages file was empty",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 0 rows, every TextMessages file "
                             "was empty",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 5 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 0 rows, "
                             "every TextMessages file was empty",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 10 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 99 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "TextMessages file in the extracted set",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no TextMessages file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 15 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, "
                             "every TextMessages file was empty",
        },
        "output_types": "standard",
        "artifact_icon": "message-square",
    },
    "ford_sync_wince_media_sources": {
        "name": "Ford SYNC WinCE - Media Sources",
        "description": "The media source the module cached in each source slot: the source's "
                       "name and the identifier string stored with it, such as a USB device's "
                       "serial and manufacturer or a Bluetooth handset's address.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From MediaCache/Source_<n>.dat, one file per slot. Tested on eight SYNC Gen1 "
                 "units: Ford Escape 2010 to 2014 (six units), Ford Edge 2013, and Ford Fusion "
                 "2019, covering Gen1 versions 2, 3, 4 and 5 and read from the file sets "
                 "extracted from each unit's flash image. Each file starts with two counted "
                 "UTF-16 strings, an identifier and a name. The identifier is either twelve "
                 "hex digits, shown with colons as a Bluetooth address, or a run of "
                 "[key:value] pairs; the keys seen were name, serial, firmware, model, "
                 "manufacturer and version, and the pairs are split into the Serial, "
                 "Manufacturer, Model and Firmware columns with the whole string kept in "
                 "Identifier. Two of the eight units put eight more bytes before the first "
                 "string, and both forms are read. The rest of each file, which reaches "
                 "several hundred kilobytes on some units, is not decoded, and File Size is "
                 "given so a large file can be told from a bare entry. Which physical port a "
                 "slot number stands for is not established here. A row records that the "
                 "module cached this source. It does not establish what was played.",
        "paths": ('*/MediaCache/Source_*.dat*',),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 5 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 5 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 2 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 5 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 5 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 5 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "Source file in the extracted set",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "its one Source file has a different layout and is not read",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 3 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 5 rows",
        },
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    },
    "ford_sync_wince_log_paired_devices": {
        "name": "Ford SYNC WinCE - Paired Devices In Log",
        "description": "Paired device lines from the module's debug log, one row per distinct "
                       "device line per log file, with the device name, handset address, "
                       "device number, primary value, pair order and how many lines repeated "
                       "it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From the 'Paired devices' blocks of Windows/LogFiles/MsgLog<n>.txt. Tested "
                 "on eight SYNC Gen1 units: Ford Escape 2010 to 2014 (six units), Ford Edge "
                 "2013, and Ford Fusion 2019, covering Gen1 versions 2, 3, 4 and 5 and read "
                 "from the file sets extracted from each unit's flash image. MsgLog files are "
                 "the unit's rolling debug log: each line starts with a number, shown as Tick "
                 "where it is reported, whose unit is not established here. The log's only "
                 "wall clock is in its 'start saving retailmsg' lines, and on all eight tested "
                 "Gen1 units every such reading fell in 2003, so it is the unit's own clock "
                 "and not a calendar date to rely on. The log repeats the paired list many "
                 "times, so identical lines are folded into one row with a Line Count and the "
                 "first and last line numbers; a device whose primary value or pair order "
                 "changed within a file has one row per combination. Primary is the line's "
                 "primary value as stored. The line's active value and its role tags are not "
                 "surfaced: the tags read [Phone Device] [Media Device] on all 811 lines "
                 "checked in the MsgLog files. The log is a rolling window, so a handset with "
                 "a phonebook or call list file can be absent here, and the reverse. The same "
                 "lines are also read from the log text saved beside a crash dump, "
                 "Windows/DumpFiles/<dump>/<dump>.RTL, which seven of the tested units "
                 "carried; of 830 lines sampled from it, one was also in the MsgLog files, and "
                 "Source File tells the two apart. It gave 20 of the 56 rows on the tested "
                 "units.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 1 row",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 5 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 2 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 4 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 8 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 4 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 12 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 20 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "ford_sync_wince_log_phone_connections": {
        "name": "Ford SYNC WinCE - Phone Connections In Log",
        "description": "Phone connect and disconnect lines from the module's debug log, with "
                       "the device name and handset address in each line, its tick and line "
                       "number, and the last log save clock reading above it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From 'APP-PHONE-CONNECT: Current device' and 'APP-PHONE-DISCONNECT: Last "
                 "device' lines of Windows/LogFiles/MsgLog<n>.txt. Only the version 5 unit "
                 "(Ford Fusion 2019) wrote these lines, 40 of them; the seven earlier units "
                 "gave no rows. MsgLog files are the unit's rolling debug log: each line "
                 "starts with a number, shown as Tick where it is reported, whose unit is not "
                 "established here. The log's only wall clock is in its 'start saving "
                 "retailmsg' lines, and on all eight tested Gen1 units every such reading fell "
                 "in 2003, so it is the unit's own clock and not a calendar date to rely on. "
                 "Last Log Save Clock Above is the reading in the nearest such line above the "
                 "event in the same file. It is context for ordering, not the time of the "
                 "event, and it is empty when no save line precedes the event. The address is "
                 "the hexadecimal value in the line, shown with colons. The log is a rolling "
                 "window and does not hold every connection. The log text saved beside a crash "
                 "dump, Windows/DumpFiles/<dump>/<dump>.RTL, is read as well; on the seven "
                 "tested units that carried it, it held no such line.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 0 rows, no such lines in the log",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 40 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 0 rows, "
                             "no such lines in the log",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "such lines in the log",
        },
        "output_types": "standard",
        "artifact_icon": "link",
    },
    "ford_sync_wince_log_gps_positions": {
        "name": "Ford SYNC WinCE - GPS Positions In Log",
        "description": "GPS readings written into the module's message log (MsgLog), one row "
                       "per line: the latitude and longitude fields as the line states them, a "
                       "decimal value derived from each, and the altitude, heading, speed and "
                       "satellite fields as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From lines of Windows/LogFiles/MsgLog<n>.txt that carry "
                 "'VehicleDataGPSChanged: CanSignal State: <state>/ GPS: LNG:<a>.<b>.<c> "
                 "LAT:<a>.<b>.<c> Alt: COMP: HEAD: SPD: SAT: FAULTY: HLAT: HLONG:'. Tested on "
                 "the log files of nine units read from their extracted file sets (eight SYNC "
                 "Gen1, one SYNC Gen2); a second Gen2 set held no log file. Only the version 5 "
                 "unit (Ford Fusion 2019) wrote such lines, 338 of them in two log files. 337 "
                 "of the 338 are warnings that a message sink needed some milliseconds to "
                 "process the reading, so the log holds the readings that were slow to process "
                 "and not a continuous track; Processing Milliseconds is that number. It is "
                 "empty on the other line, which is a fragment: it begins mid-word, follows a "
                 "save line, and has no Tick. The position fields are three numbers each. On "
                 "the tested unit the third number never started with a zero: of its 676 "
                 "values none started with a zero, 64 ended with one, and 45 had fewer than "
                 "four digits. The derived columns read it as ten-thousandths of the second "
                 "number and not as digits after a decimal point. That reading rests on this "
                 "pattern alone and is not taken from the unit's code. The derived columns "
                 "read the second and third numbers as minutes and the first as degrees with "
                 "89 subtracted for latitude and 179 for longitude, the minutes moving the "
                 "value away from zero. Those two offsets are not taken from the unit's own "
                 "code. They are the ones that reproduce an independent parse of the same "
                 "unit, which gave the same latitude on 320 and the same longitude on 311 of "
                 "the 338 lines to four decimals; the remaining 18 and 27 lines all have a "
                 "third number shorter than four digits, which that parse reads as decimal "
                 "digits and this one as ten-thousandths. The lines where the two agree cannot "
                 "decide between the readings, because a four-digit value reads the same both "
                 "ways. Treat the derived columns as a reading to confirm, and the as stored "
                 "columns as what the line holds. The units of Alt, HEAD and SPD are not "
                 "established here and they are shown as stored: on the tested unit HEAD ran "
                 "from 4 to 35994 and SPD from 0 to 56. FAULTY (as stored) held one value, 0, "
                 "on all 338 rows, HLAT (as stored) and HLONG (as stored) each held one value, "
                 "2, on all 338 rows, and Signal State held one value, Valid, on all 338 rows; "
                 "what FAULTY, HLAT and HLONG stand for is not established here. Log lines "
                 "start with a number, shown as Tick, whose unit is not established here; the "
                 "fragment line has none. The log's only dated clock reading is in its 'start "
                 "saving retailmsg' lines, and on the tested unit every such reading fell in "
                 "2003, so it is the unit's own clock and not a calendar date to rely on. Last "
                 "Log Save Clock Above is the nearest such reading above the line in the same "
                 "file. It is context for ordering, not the time of the reading, and it is "
                 "empty when no save line precedes the line. The log text saved beside a crash "
                 "dump, Windows/DumpFiles/<dump>/<dump>.RTL, is read as well. Seven of the "
                 "tested units had one or more, 13 files in all, and none held such a line.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no"
                             " such lines in the log",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no"
                             " such lines in the log",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 0 rows, no"
                             " such lines in the log",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 0 rows, no"
                             " such lines in the log",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 338 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no"
                             " such lines in the log",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 "
                             "rows, no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 0 rows,"
                             " no such lines in the log",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 0 rows, no"
                             " such lines in the log",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
    "ford_sync_wince_log_odometer": {
        "name": "Ford SYNC WinCE - Odometer Readings In Log",
        "description": "Odometer values the module's debug log recorded, one row per distinct "
                       "value per log file, with both numbers the line carries and how many "
                       "lines repeated them.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From 'GetOdometerReading() ODO = <a> (<b>)' lines of "
                 "Windows/LogFiles/MsgLog<n>.txt. Tested on eight SYNC Gen1 units: Ford Escape "
                 "2010 to 2014 (six units), Ford Edge 2013, and Ford Fusion 2019, covering "
                 "Gen1 versions 2, 3, 4 and 5 and read from the file sets extracted from each "
                 "unit's flash image. Six units carried such lines and two did not (the 2013 "
                 "Edge and the version 5 Fusion). MsgLog files are the unit's rolling debug "
                 "log: each line starts with a number, shown as Tick where it is reported, "
                 "whose unit is not established here. The log's only wall clock is in its "
                 "'start saving retailmsg' lines, and on all eight tested Gen1 units every "
                 "such reading fell in 2003, so it is the unit's own clock and not a calendar "
                 "date to rely on. The line does not label its two numbers. On every tested "
                 "row the first divided by the second was between 1.6093 and 1.6094, the ratio "
                 "of kilometres to miles, so the first is consistent with kilometres and the "
                 "second with miles; that is a reading of the data, not a documented unit. The "
                 "log repeats the value many times, so identical lines are folded into one row "
                 "with a Line Count. Last Log Save Clock Above is the nearest log save reading "
                 "above the first such line and is empty when none precedes it. The same lines "
                 "are also read from the log text saved beside a crash dump, "
                 "Windows/DumpFiles/<dump>/<dump>.RTL, which seven of the tested units "
                 "carried; of 830 lines sampled from it, one was also in the MsgLog files, and "
                 "Source File tells the two apart. It gave 41 of the 95 rows on the tested "
                 "units, and the ratio held on those too.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 2 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 1 row",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 1 row",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 17 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 47 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 27 rows",
        },
        "output_types": "standard",
        "artifact_icon": "activity",
    },
    "ford_sync_wince_log_clock_readings": {
        "name": "Ford SYNC WinCE - Log Save Clock Readings",
        "description": "The wall clock readings in the module's debug log: one row per 'start "
                       "saving retailmsg' line, with the clock value the line states, its tick "
                       "and its line number.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From 'SYSHEALTH: start saving retailmsg at <date> <time>' lines of "
                 "Windows/LogFiles/MsgLog<n>.txt. Tested on eight SYNC Gen1 units: Ford Escape "
                 "2010 to 2014 (six units), Ford Edge 2013, and Ford Fusion 2019, covering "
                 "Gen1 versions 2, 3, 4 and 5 and read from the file sets extracted from each "
                 "unit's flash image. MsgLog files are the unit's rolling debug log: each line "
                 "starts with a number, shown as Tick where it is reported, whose unit is not "
                 "established here. The log's only wall clock is in its 'start saving "
                 "retailmsg' lines, and on all eight tested Gen1 units every such reading fell "
                 "in 2003, so it is the unit's own clock and not a calendar date to rely on. "
                 "The date is read month first: across the 110 such lines on the tested units "
                 "a value above 12 occurs 43 times in the second position and never in the "
                 "first. The reading is written out as if it were UTC with no offset applied. "
                 "These rows let an examiner place other log lines relative to the unit's own "
                 "clock. They do not give a calendar date. A SYNC Gen2 unit (2014 Ford Edge "
                 "SEL) wrote the same line six times, with readings from 2010 to 2019. The log "
                 "text saved beside a crash dump, Windows/DumpFiles/<dump>/<dump>.RTL, is read "
                 "as well; on the seven tested units that carried it, it held no such line.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 10 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 7 rows",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 6 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 4 rows",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 6 rows",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 64 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 6 rows",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 8 rows",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 5 rows",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
    },
    "ford_sync_wince_unit_info": {
        "name": "Ford SYNC WinCE - Unit Information",
        "description": "Identifying values the module's debug log states: the VIN in "
                       "VinService lines and the software build string in Build Information "
                       "lines, one row per distinct value per log file.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/LogFiles/MsgLog<n>.txt. Tested on eight SYNC Gen1 units: Ford "
                 "Escape 2010 to 2014 (six units), Ford Edge 2013, and Ford Fusion 2019, "
                 "covering Gen1 versions 2, 3, 4 and 5 and read from the file sets extracted "
                 "from each unit's flash image. Build Information lines were present on four "
                 "units and a VinService VIN line on the version 5 unit only; three units gave "
                 "no rows because their log window held neither. MsgLog files are the unit's "
                 "rolling debug log: each line starts with a number, shown as Tick where it is "
                 "reported, whose unit is not established here. The log's only wall clock is "
                 "in its 'start saving retailmsg' lines, and on all eight tested Gen1 units "
                 "every such reading fell in 2003, so it is the unit's own clock and not a "
                 "calendar date to rely on. Values are reported as the log states them. The "
                 "same lines are also read from the log text saved beside a crash dump, "
                 "Windows/DumpFiles/<dump>/<dump>.RTL, which seven of the tested units "
                 "carried; of 830 lines sampled from it, one was also in the MsgLog files, and "
                 "Source File tells the two apart. It gave 8 of the 16 rows on the tested "
                 "units. The module's registry hives (Documents and Settings/system.hv and "
                 "user.hv) are not read by this module, so identity values held only there are "
                 "not reported.",
        "paths": ('*/Windows/LogFiles/MsgLog*.txt*', '*/Windows/DumpFiles/*.RTL'),
        "sample_data": {
            "xtrmp_item002": "2013 Ford Edge, SYNC Gen1v2, extracted file set | 6 rows",
            "xtrmp_item003": "2012 Ford Escape, SYNC Gen1v2 | 0 rows, no such lines in the log",
            "xtrmp_item004": "2010 Ford Escape, SYNC Gen1v2, extracted file set | 3 rows",
            "xtrmp_item008": "2011 Ford Escape, SYNC Gen1v4, extracted file set | 1 row",
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 2 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "such lines in the log",
            "xtrmp_item016": "2011 Ford Explorer XLT, SYNC Gen2, extracted file set | 0 rows, "
                             "no MsgLog file in the extracted set",
            "xtrmp_item065": "2014 Ford Escape SE, SYNC Gen1v3, extracted file set | 0 rows, "
                             "no such lines in the log",
            "xtrmp_item066": "2011 Ford Escape, SYNC Gen1v2, extracted file set | 4 rows",
        },
        "output_types": "standard",
        "artifact_icon": "info",
    },
}

# Derived by comparison, not documented: see the Call History notes.
CALL_LISTS = {'0x10000': 'Incoming', '0x20000': 'Outgoing', '0x40000': 'Missed'}

_PB_SIGNATURE = bytes.fromhex('036068c0')
# Text message record layouts by record size: (time offset, flag offset).
_MESSAGE_LAYOUTS = {988: (0x3c6, 0x3d8), 1072: (0x416, 0x428)}
_NUMBER_OFFSET, _NAME_OFFSET, _BODY_OFFSET = 0x000, 0x202, 0x284

_ADDRESS_IN_NAME = re.compile(r'([0-9A-Fa-f]{12})')
_CALL_HISTORY = re.compile(r'<CallHistory\s+type="([^"]*)"\s*(?:/>|>(.*?)</CallHistory>)', re.S)
_CALL = re.compile(r'<Call\b([^>]*?)/?>')
_ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
_DEVICE_ID = re.compile(r'<Device\s+id="([^"]*)"')
_BRACKET_PAIR = re.compile(r'\[([A-Za-z]+):([^\]]*)\]')

_LOG_LINE = re.compile(r'^(\d+)\s')
_LOG_DEVICE = re.compile(
    r'device: (\d+)\. \[(.*)\] \[0x0000([0-9A-Fa-f]{12})\], active = (\d+), '
    r'primary = (\d+), pairorder = (\d+) ?, (.*)$')
_LOG_ODOMETER = re.compile(r'GetOdometerReading\(\)\s+ODO = (\d+) \((\d+)\)')
_LOG_SAVE = re.compile(r'SYSHEALTH: start saving retailmsg at '
                       r'(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)')
_LOG_CONNECT = re.compile(r"APP-PHONE-(CONNECT: Current|DISCONNECT: Last) device: "
                          r"'(.*)' \(0x([0-9A-Fa-f]+)\)")
_LOG_GPS = re.compile(
    r'(?:needed (\d+) ms to process )?VehicleDataGPSChanged: CanSignal State: (\S+?)/ GPS: '
    r'LNG:(\d+)\.(\d+)\.(\d+) LAT:(\d+)\.(\d+)\.(\d+) Alt:(-?\d+) COMP:(\d+/\d+) '
    r'HEAD:(\d+) SPD:(\d+) SAT:(\d+) FAULTY:(\d+) HLAT:(\d+) HLONG:(\d+)')
_LOG_VIN = re.compile(r'VinService: VIN \[([^\]]*)\]')
_LOG_BUILD = re.compile(r'\* Build Information: (\S+)')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return b''


def _address(text):
    """Twelve hex digits as aa:bb:cc:dd:ee:ff; anything else is returned as given."""
    if re.fullmatch(r'[0-9A-Fa-f]{12}', text or ''):
        return ':'.join(text[i:i + 2] for i in range(0, 12, 2)).lower()
    return text or ''


def _address_from_name(path, prefix):
    base = os.path.basename(path)
    if not base.startswith(prefix):
        return ''
    match = _ADDRESS_IN_NAME.match(base[len(prefix):])
    return _address(match.group(1)) if match else ''


def _unescape(text):
    for entity, char in (('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&apos;', "'"),
                         ('&amp;', '&')):
        text = text.replace(entity, char)
    return text


def _compact_time(text):
    """'YYYYMMDDTHHMMSS' as 'YYYY-MM-DD HH:MM:SS'; '' when it is anything else."""
    try:
        return datetime.strptime(text, '%Y%m%dT%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return ''


# ---------------------------------------------------------------------------
# Call history
# ---------------------------------------------------------------------------

@artifact_processor
def ford_sync_wince_call_history(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        if not os.path.basename(file_found).startswith('CH'):
            continue
        text = _read(file_found).decode('utf-8', 'replace')
        device = _DEVICE_ID.search(text)
        if device is None:
            continue
        source_paths.append(file_found)
        address = _address(device.group(1))
        for list_type, body in _CALL_HISTORY.findall(text):
            for position, call in enumerate(_CALL.findall(body or ''), start=1):
                attributes = dict(_ATTRIBUTE.findall(call))
                data_list.append((
                    _compact_time(attributes.get('time', '')),
                    CALL_LISTS.get(list_type, ''), list_type,
                    _unescape(attributes.get('name', '')),
                    _unescape(attributes.get('num', '')), position, address,
                    context.get_relative_path(file_found)))

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Call List Type (as stored)',
                    'Name', 'Phone Number', 'Position In List', 'Handset Address',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Phonebook
# ---------------------------------------------------------------------------

def _parse_phonebook(data):
    """Contacts of a PB file as (name, [(number type, number), ...]); None if unframed.

    Layout: u32 length of everything after it, a four-byte signature, u32 contact count,
    then per contact a u32 record length, a length-prefixed name, a u16 number count and
    per number a u16 type and a length-prefixed string. All little-endian; strings carry
    their terminating NUL inside the stated length.
    """
    if len(data) < 12 or data[4:8] != _PB_SIGNATURE:
        return None
    if struct.unpack('<I', data[0:4])[0] != len(data) - 4:
        return None
    count = struct.unpack('<I', data[8:12])[0]
    offset = 12
    contacts = []
    try:
        for _ in range(count):
            record_len = struct.unpack('<I', data[offset:offset + 4])[0]
            pos, end = offset + 4, offset + 4 + record_len
            if end > len(data):
                return None
            name_len = struct.unpack('<H', data[pos:pos + 2])[0]
            name = data[pos + 2:pos + 2 + name_len]
            pos += 2 + name_len
            number_count = struct.unpack('<H', data[pos:pos + 2])[0]
            pos += 2
            numbers = []
            for _ in range(number_count):
                number_type, number_len = struct.unpack('<HH', data[pos:pos + 4])
                numbers.append((number_type, data[pos + 4:pos + 4 + number_len]))
                pos += 4 + number_len
            if pos != end:
                return None
            contacts.append((name, numbers))
            offset = end
    except struct.error:
        return None
    if offset != len(data):
        return None
    return contacts


def _c_string(raw):
    return raw.split(b'\x00', 1)[0].decode('utf-8', 'replace')


@artifact_processor
def ford_sync_wince_phonebook(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if not base.startswith('PB'):
            continue
        contacts = _parse_phonebook(_read(file_found))
        if contacts is None:
            logfunc(f'Ford SYNC WinCE phonebook: {base} does not have the expected framing, '
                    'not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, 'PB')
        for position, (name, numbers) in enumerate(contacts, start=1):
            data_list.append((
                address, _c_string(name),
                '; '.join(_c_string(number) for _type, number in numbers),
                '; '.join(str(number_type) for number_type, _number in numbers),
                len(numbers), position, context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'Name', 'Phone Numbers',
                    'Number Types (as stored)', 'Number Count', 'Position In File',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_persistent_phonebook(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        named = re.match(r'persistentPhonebook_([0-9A-Fa-f]{12})', base)
        if not named:
            continue
        raw = _read(file_found)
        try:
            text = raw.decode('utf-8')
            read_as = 'UTF-8'
        except UnicodeDecodeError:
            text = raw.decode('cp1252', 'replace')
            read_as = 'Windows-1252'
        names = [line for line in text.replace('\r\n', '\n').split('\n') if line]
        if names:
            source_paths.append(file_found)
        address = ':'.join(named.group(1)[i:i + 2] for i in range(0, 12, 2)).lower()
        for position, name in enumerate(names, start=1):
            data_list.append((address, name, position, read_as,
                              context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'Name', 'Position In File', 'Text Read As',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Text messages
# ---------------------------------------------------------------------------

def _wide_string(record, start, end):
    raw = record[start:end]
    raw = raw[:len(raw) - len(raw) % 2]
    chars = []
    for i in range(0, len(raw), 2):
        if raw[i:i + 2] == b'\x00\x00':
            break
        chars.append(raw[i:i + 2])
    return b''.join(chars).decode('utf-16-le', 'replace')


def _system_time(raw):
    """A 16-byte Windows SYSTEMTIME as 'YYYY-MM-DD HH:MM:SS', or None if not a valid one."""
    year, month, _weekday, day, hour, minute, second, millis = struct.unpack('<8H', raw)
    if millis > 999:
        return None
    try:
        return datetime(year, month, day, hour, minute, second).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def _parse_messages(data):
    """Message records, or None when the file fits no known record size."""
    for record_size, (time_offset, flag_offset) in _MESSAGE_LAYOUTS.items():
        if not data or len(data) % record_size:
            continue
        rows = []
        for index in range(len(data) // record_size):
            record = data[index * record_size:(index + 1) * record_size]
            stamp = _system_time(record[time_offset:time_offset + 16])
            if stamp is None:
                rows = None
                break
            rows.append((stamp, _wide_string(record, _NUMBER_OFFSET, _NAME_OFFSET),
                         _wide_string(record, _NAME_OFFSET, _BODY_OFFSET),
                         _wide_string(record, _BODY_OFFSET, time_offset),
                         struct.unpack('<I', record[flag_offset:flag_offset + 4])[0],
                         index + 1))
        if rows is not None:
            return rows
    return None


@artifact_processor
def ford_sync_wince_text_messages(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if not base.startswith('TextMessages_'):
            continue
        data = _read(file_found)
        if not data:
            continue
        rows = _parse_messages(data)
        if rows is None:
            logfunc(f'Ford SYNC WinCE text messages: {base} ({len(data)} bytes) fits no known '
                    'record layout, not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, 'TextMessages_')
        for stamp, number, name, body, flag, position in rows:
            data_list.append((stamp, number, name, body, flag, position, address,
                              context.get_relative_path(file_found)))

    data_headers = (('Message Time', 'datetime'), 'Phone Number', 'Name', 'Message',
                    'Flag (as stored)', 'Record Number', 'Handset Address', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Media sources
# ---------------------------------------------------------------------------

def _counted_wide(data, offset):
    count = struct.unpack('<I', data[offset:offset + 4])[0]
    end = offset + 4 + 2 * count
    if count > 1024 or end > len(data):
        raise ValueError('string length')
    return data[offset + 4:end].decode('utf-16-le', 'replace'), end


def _parse_media_source(data):
    """(identifier, name) from a Source file's two leading counted strings, or None.

    The file starts with 0xFF. Later software puts eight more bytes (01 00 00 00 05 00
    15 00 on the tested units) before the first string; both forms are accepted and
    anything else is refused.
    """
    if len(data) < 9 or data[0] != 0xff:
        return None
    for start in (1, 9):
        try:
            identifier, offset = _counted_wide(data, start)
            name, _offset = _counted_wide(data, offset)
        except (ValueError, struct.error):
            continue
        if identifier and identifier.isprintable() and name.isprintable():
            return identifier, name
    return None


@artifact_processor
def ford_sync_wince_media_sources(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        slot = re.match(r'Source_(-?\d+)\.dat', base)
        if not slot:
            continue
        data = _read(file_found)
        parsed = _parse_media_source(data)
        if parsed is None:
            logfunc(f'Ford SYNC WinCE media sources: {base} does not start with the expected '
                    'strings, not read')
            continue
        source_paths.append(file_found)
        identifier, name = parsed
        fields = {key.lower(): value for key, value in _BRACKET_PAIR.findall(identifier)}
        data_list.append((
            int(slot.group(1)), name,
            fields.get('serial', '') if fields else _address(identifier),
            fields.get('manufacturer', ''), fields.get('model', ''),
            fields.get('firmware', fields.get('version', '')), identifier, len(data),
            context.get_relative_path(file_found)))

    data_headers = ('Source Slot', 'Name', 'Serial Or Address', 'Manufacturer', 'Model',
                    'Firmware Or Version', 'Identifier (as stored)', 'File Size (bytes)',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Message log
# ---------------------------------------------------------------------------

def _log_files(context):
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if base.startswith('MsgLog') or base.upper().endswith('.RTL'):
            yield file_found


def _log_lines(path):
    """(line number, tick, text, last save clock seen above) for each line of a log.

    The tick is the number the unit writes at the start of a line. The save clock is
    the wall-clock reading in the nearest 'start saving retailmsg' line above, which is
    the only clock the log carries.
    """
    text = _read(path).decode('utf-8', 'replace')
    save_clock = ''
    for number, line in enumerate(text.split('\n'), start=1):
        line = line.rstrip('\r')
        tick = _LOG_LINE.match(line)
        save = _LOG_SAVE.search(line)
        if save:
            month, day, year, hour, minute, second = save.groups()
            save_clock = f'{year}-{month}-{day} {hour}:{minute}:{second}'
        yield number, int(tick.group(1)) if tick else '', line, save_clock


def _valid_clock(text):
    try:
        datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''
    return text


@artifact_processor
def ford_sync_wince_log_paired_devices(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        seen = {}
        for number, _tick, line, _clock in _log_lines(file_found):
            match = _LOG_DEVICE.search(line)
            if not match:
                continue
            index, name, address, _active, primary, order, _roles = match.groups()
            key = (name, address.lower(), index, primary, order)
            if key in seen:
                seen[key][0] += 1
                seen[key][2] = number
            else:
                seen[key] = [1, number, number]
        if seen:
            source_paths.append(file_found)
        for (name, address, index, primary, order), counts in seen.items():
            data_list.append((name, _address(address), int(index), int(primary), int(order),
                              counts[0], counts[1], counts[2],
                              context.get_relative_path(file_found)))

    data_headers = ('Device Name', 'Handset Address', 'Device Number', 'Primary (as stored)',
                    'Pair Order', 'Line Count', 'First Line', 'Last Line',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_phone_connections(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        found = False
        for number, tick, line, clock in _log_lines(file_found):
            match = _LOG_CONNECT.search(line)
            if not match:
                continue
            found = True
            event = 'Connect' if match.group(1).startswith('CONNECT') else 'Disconnect'
            data_list.append((_valid_clock(clock), event, match.group(2),
                              _address(match.group(3).rjust(12, '0')[-12:]), tick, number,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = (('Last Log Save Clock Above', 'datetime'), 'Event', 'Device Name',
                    'Handset Address', 'Tick', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _gps_decimal(degrees, minutes, fraction, offset):
    """Decimal degrees from one position field, or '' when the minutes do not fit.

    The third number is ten-thousandths of a minute. The offset is the value taken from
    the first number; see the artifact notes for what supports it.
    """
    if len(fraction) > 4 or int(minutes) > 59:
        return ''
    whole = int(degrees) - offset
    part = (int(minutes) + int(fraction) / 10000) / 60
    return round(whole - part if whole < 0 else whole + part, 6)


@artifact_processor
def ford_sync_wince_log_gps_positions(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        found = False
        for number, tick, line, clock in _log_lines(file_found):
            match = _LOG_GPS.search(line)
            if not match:
                continue
            found = True
            (needed, state, lng_d, lng_m, lng_f, lat_d, lat_m, lat_f, alt, comp, head, speed,
             sats, faulty, hlat, hlong) = match.groups()
            data_list.append((
                _valid_clock(clock), _gps_decimal(lat_d, lat_m, lat_f, 89),
                _gps_decimal(lng_d, lng_m, lng_f, 179), f'{lat_d}.{lat_m}.{lat_f}',
                f'{lng_d}.{lng_m}.{lng_f}', int(alt), comp, int(head), int(speed), int(sats),
                int(faulty), int(hlat), int(hlong), state,
                int(needed) if needed else '', tick, number,
                context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = (('Last Log Save Clock Above', 'datetime'), 'Latitude (derived)',
                    'Longitude (derived)', 'LAT (as stored)', 'LNG (as stored)',
                    'Alt (as stored)', 'COMP (as stored)', 'HEAD (as stored)',
                    'SPD (as stored)', 'SAT (as stored)', 'FAULTY (as stored)',
                    'HLAT (as stored)', 'HLONG (as stored)', 'Signal State',
                    'Processing Milliseconds', 'Tick', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_odometer(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        seen = {}
        for number, _tick, line, clock in _log_lines(file_found):
            match = _LOG_ODOMETER.search(line)
            if not match:
                continue
            key = (int(match.group(1)), int(match.group(2)))
            if key in seen:
                seen[key][0] += 1
                seen[key][2] = number
            else:
                seen[key] = [1, number, number, clock]
        if seen:
            source_paths.append(file_found)
        for (first, second), counts in seen.items():
            data_list.append((_valid_clock(counts[3]), first, second, counts[0], counts[1],
                              counts[2], context.get_relative_path(file_found)))

    data_headers = (('Last Log Save Clock Above', 'datetime'), 'Odometer Value',
                    'Value In Parentheses', 'Line Count', 'First Line', 'Last Line',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_log_clock_readings(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        found = False
        for number, tick, line, clock in _log_lines(file_found):
            if not _LOG_SAVE.search(line) or not _valid_clock(clock):
                continue
            found = True
            data_list.append((clock, tick, number, context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = (('Log Save Clock', 'datetime'), 'Tick', 'Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_sync_wince_unit_info(context):
    data_list = []
    source_paths = []
    for file_found in _log_files(context):
        seen = {}
        for number, _tick, line, _clock in _log_lines(file_found):
            for label, pattern in (('VIN In Log', _LOG_VIN),
                                   ('Build Information', _LOG_BUILD)):
                match = pattern.search(line)
                if not match or not match.group(1).strip():
                    continue
                key = (label, match.group(1).strip())
                if key in seen:
                    seen[key][0] += 1
                else:
                    seen[key] = [1, number]
        if seen:
            source_paths.append(file_found)
        for (label, value), counts in seen.items():
            relative = context.get_relative_path(file_found)
            data_list.append((label, value, counts[0], counts[1], relative))
            device_info('Ford SYNC WinCE', label, value, relative)

    data_headers = ('Property', 'Value', 'Line Count', 'First Line', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
