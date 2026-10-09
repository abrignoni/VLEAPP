"""GM OnStar telematics module built by LG, generations 9 and 10.

Named for the module, not a vehicle brand: the same module is fitted across GM brands,
and the samples behind this file are Chevrolet, GMC and Buick vehicles. The two
generations keep different files under the same var/ tree:

    Generation 9   var/sysinfo/BT.dat         five fixed Bluetooth device slots
                   var/BTfeature/phoneNN.pb   one self-describing phonebook per slot
                   obn/storage/gps            20-byte position records, one per second
                   obn/storage/flight         the turn-by-turn navigation text log
    Generation 10  var/sysinfo/*.dat          text files of [section] and key=value lines
    Both           var/log/poweroff.log       one line: a clock reading and two numbers
                   var/ver.txt                the software version

Generation 9 also has binary phone.dat, vifdata.dat and occ.dat files. They are raw
structures with no framing this module can check, and they are not read.
"""

import os
import re
import sqlite3
import struct
from datetime import datetime

from scripts.ilapfuncs import (artifact_processor, device_info, logfunc,
                               open_sqlite_db_readonly)

__artifacts_v2__ = {
    "gm_onstar_lg_bt_devices": {
        "name": "GM OnStar LG Gen9 - Bluetooth Devices",
        "description": "The Bluetooth device slots the telematics module stores, with the "
                       "device number, name and Bluetooth address held in each occupied slot.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/sysinfo/BT.dat. Tested on four generation 9 units: a 2012 Chevrolet "
                 "Cruze LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick "
                 "Enclave, read from the file sets extracted from each unit's flash image. The "
                 "file is 323 bytes: an 8-byte header, five 60-byte slots and a '<SysInfo' "
                 "tag, and a file without that shape is logged and not read. A slot with no "
                 "name and device number 0 is left out. The address is stored in three parts "
                 "and is assembled here as non-significant, upper and lower part. That "
                 "assembly is checked by the data: for all eight phonebook files on the two "
                 "units that had them, the address in the phonebook file's own header equalled "
                 "the address assembled for the slot with the same device number. Three units "
                 "held four occupied slots each and one held none. The eight bytes at the end "
                 "of each slot are not decoded. An extraction can hold several copies of one "
                 "file, marked (Deleted) or (CopyN) in the name. Files with identical content "
                 "are read once and Identical Files gives how many there were. A slot records "
                 "that the module held a pairing entry for the device. It does not establish "
                 "who carried it. Generation 10 units have no BT.dat.",
        "paths": ('*/var/sysinfo/BT.dat*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 4 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 4 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, BT.dat held no occupied slot",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 4 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "no BT.dat on generation 10",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, no BT.dat on "
                             "generation 10",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "gm_onstar_lg_phonebook": {
        "name": "GM OnStar LG Gen9 - Phonebook",
        "description": "Contacts in the phonebook file the telematics module keeps for each "
                       "Bluetooth device number, with the last name, first name and the home, "
                       "work, mobile and other numbers stored for each contact.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/BTfeature/phoneNN.pb, where NN is the device number of a slot in "
                 "BT.dat. Tested on four generation 9 units: a 2012 Chevrolet Cruze LT, a 2012 "
                 "GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave, read from "
                 "the file sets extracted from each unit's flash image. Two of them held "
                 "phonebook files, four each. The file starts with the signature GMPB and the "
                 "handset's address, then lists its own fields by id and name, then holds "
                 "records of (field id, length, value) entries. All eight tested files parsed "
                 "to their exact end under that layout, and a file that does not is logged and "
                 "not read. The field names are the file's own. Every tested file also "
                 "declared a seventh field, Call History Time Stamp, and no record used it, so "
                 "it has no column. A contact with two values for one field has them joined "
                 "with a semicolon. Handset Address is the address in the file header. An "
                 "extraction can hold several copies of one file, marked (Deleted) or (CopyN) "
                 "in the name. Files with identical content are read once and Identical Files "
                 "gives how many there were. A record establishes that the module held the "
                 "contact for that device. It does not establish that any number was dialled.",
        "paths": ('*/var/BTfeature/phone*.pb*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 244 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 1119 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, no phoneNN.pb file in the extracted set",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, no "
                             "phoneNN.pb file in the extracted set",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "no phoneNN.pb file in the extracted set",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, no phoneNN.pb file in "
                             "the extracted set",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "gm_onstar_lg_gps_reports": {
        "name": "GM OnStar LG Gen10 - GPS Reports",
        "description": "GPS reports the telematics module stored, with the UTC time, latitude "
                       "and longitude of each report and the elevation, speed, course, "
                       "dilution of precision and satellite count stored with it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From the GPSRegularReport sections of the state files under var/sysinfo and "
                 "of the module's raw flash image, DiskImages/NORimage.bin, when the "
                 "extraction carries it. Tested on two generation 10 units: a 2016 Chevrolet "
                 "Cruze and a 2017 Buick Encore. A state file is text of [section] and "
                 "key=value lines that opens with a [*] section and ends at an end-of-file "
                 "byte. The extraction also holds 65,535-byte copies of these files in which "
                 "several such documents, of that file or of another, follow one another; "
                 "every document in every .dat file is read, each from its [*] line to its end "
                 "byte. A row found in more than one document is reported once, with Times "
                 "Found, and Source File and Document Offset say where it was first read. The "
                 "current gps.dat holds ten reports. Reading the embedded documents in the "
                 "files gave 111 distinct reports on the Cruze and 64 on the Encore, and "
                 "reading the flash image as well gave 1,139 and 541. The image holds the same "
                 "documents with no file system around them, including ones the file system "
                 "has released. Timestamp is built from the report's utc_year to utc_sec keys, "
                 "with the fraction of a second dropped, and is UTC: on 1,679 of the 1,680 "
                 "tested reports the report's own GPS week and time of week, converted to a "
                 "date, was between 18 and 19 seconds ahead of that reading, and 18 seconds is "
                 "the GPS to UTC offset in force since 2017. Latitude and Longitude are the "
                 "stored eight-byte values divided by 10,000,000. That scale is derived by "
                 "comparison: on the Encore an independent parse of the same unit listed 541 "
                 "points, the same 541 timestamps read here, and every position agreed to "
                 "within 0.000001 degree. Elevation, Speed Over Ground and Course Over Ground "
                 "are shown as stored because their units are not established here. Reports "
                 "whose latitude and longitude are both zero are left out. The other keys of "
                 "each report (variances, velocity vectors, fix flags) are not surfaced. Rows "
                 "are sorted newest first. A report records where the module's receiver placed "
                 "itself at that time. It does not establish who was in the vehicle. "
                 "Generation 9 units have no gps.dat; their positions are in the GPS Track "
                 "artifact.",
        "paths": ('*/var/sysinfo/*.dat*', '*/DiskImages/NORimage.bin'),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, no gps.dat on generation 9",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 0 rows, no "
                             "gps.dat on generation 9",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, no gps.dat on generation 9",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, no "
                             "gps.dat on generation 9",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, acquisition folder with "
                             "flash image | 1139 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 541 rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "gm_onstar_lg_power_off_log": {
        "name": "GM OnStar LG - Power Off Log",
        "description": "Power-off records the telematics module wrote, one per poweroff.log "
                       "file, with the clock reading in the record and the two numbers that "
                       "follow it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/log/poweroff.log, a one-line file holding a date and time, a comma "
                 "and two numbers. Tested on four generation 9 units: a 2012 Chevrolet Cruze "
                 "LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave, "
                 "read from the file sets extracted from each unit's flash image. Tested on "
                 "two generation 10 units: a 2016 Chevrolet Cruze and a 2017 Buick Encore. "
                 "Across the six units all rows but one came from copies the acquisition "
                 "marked (Deleted), between 5 and 185 distinct ones per unit. The record does "
                 "not state a time zone. On the two generation 10 units the latest reading was "
                 "within three seconds of a GPS report whose time is UTC, so the clock is "
                 "consistent with UTC there; for generation 9 that is not established. "
                 "Readings of 1970-01-01 00:00:00 occur on three units and do not give a date. "
                 "The two numbers are shown as stored: the first was 1 on every tested row and "
                 "the second was 0 or 1, and nothing available here documents them. An "
                 "extraction can hold several copies of one file, marked (Deleted) or (CopyN) "
                 "in the name. Files with identical content are read once and Identical Files "
                 "gives how many there were. On one unit an independent parse reported the "
                 "same 185 times. A row records that the module wrote a power-off record with "
                 "that reading. What triggered it is not established.",
        "paths": ('*/var/log/poweroff.log*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 5 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 13 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 113 "
                             "rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 185 rows",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "gm_onstar_lg_stored_values": {
        "name": "GM OnStar LG Gen10 - Stored Values",
        "description": "Selected values from the generation 10 module's text state files: the "
                       "redial and recall numbers, the module's own mobile numbers, "
                       "destination coordinates and text, stolen-vehicle and dealer values, "
                       "and the unit expiry date, each with the save time of the document it "
                       "came from.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From the state files under var/sysinfo and the module's raw flash image, "
                 "DiskImages/NORimage.bin, when the extraction carries it. Tested on two "
                 "generation 10 units: a 2016 Chevrolet Cruze and a 2017 Buick Encore. A state "
                 "file is text of [section] and key=value lines that opens with a [*] section "
                 "and ends at an end-of-file byte. The extraction also holds 65,535-byte "
                 "copies of these files in which several such documents, of that file or of "
                 "another, follow one another; every document in every .dat file is read, each "
                 "from its [*] line to its end byte. A row found in more than one document is "
                 "reported once, with Times Found, and Source File and Document Offset say "
                 "where it was first read. A row is reported only when the key holds a value "
                 "other than empty, 0 or -1, so most keys give no row. With the flash image "
                 "read as well, the Cruze gave 15 rows (the OTUBMgmnt expiry year, month and "
                 "day, and one redial number in twelve documents with different save times) "
                 "and the Encore 35 (the same expiry keys and a lock-out counter in 32 "
                 "documents). Section and Key are the file's own names and no meaning beyond "
                 "the name is established here. Values stored as hexadecimal bytes are shown "
                 "as text when they are printable ASCII. The destination, name tag and recent "
                 "destination lists were empty on both units; their numbered sections are "
                 "reported whole when present, and that path has not been exercised on real "
                 "data. Document Save Time is the TimeStamp in the document's first section; "
                 "several documents carried 1970 readings. Not surfaced: the diagnostic "
                 "trouble codes, the data identifier tables, the display device and "
                 "customisation tables, the authentication key in tcuid.dat, and the empty "
                 "alerts.db.",
        "paths": ('*/var/sysinfo/*.dat*', '*/DiskImages/NORimage.bin'),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, generation 9 files are not in the text format",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 0 rows, "
                             "generation 9 files are not in the text format",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, generation 9 files are not in the text format",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "generation 9 files are not in the text format",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, acquisition folder with "
                             "flash image | 15 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 35 rows",
        },
        "output_types": "standard",
        "artifact_icon": "list",
    },
    "gm_onstar_lg_gps_track": {
        "name": "GM OnStar LG Gen9 - GPS Track",
        "description": "Position records the telematics module's navigation storage holds, one "
                       "per second, with the time, latitude, longitude, speed and heading of "
                       "each record.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From obn/storage/gps, a file of 20-byte big-endian records. Tested on four "
                 "generation 9 units (a 2012 Chevrolet Cruze LT, a 2012 GMC Acadia, a 2014 GMC "
                 "Sierra 1500 SLE and a 2011 Buick Enclave), read from the file sets extracted "
                 "from each unit's flash image. Only the Acadia held data here; on the other "
                 "three the file was present and zero bytes long, and it is also zero bytes on "
                 "the two tested generation 10 units. The Acadia's file held 12,800 records "
                 "dated from November 2015 to April 2017. Latitude and Longitude are the "
                 "stored integers divided by 6,000,000. That scale is the unit's own: the "
                 "navigation log beside this file prints the same kind of integer next to its "
                 "decimal degrees. It was also checked by comparison: for all 12,782 records "
                 "whose timestamp was unique, an independent parse of the same unit gave the "
                 "same position to within 0.000002 degree. Speed is the stored value read as "
                 "millimetres per second and shown in km/h, and Heading is the upper nine bits "
                 "of the stored heading value. Both readings are derived by comparison with "
                 "that independent parse, which computed its own speed and bearing between "
                 "points: the median difference was 0.05 km/h and 1 degree over 10,361 records "
                 "above 30 km/h. The lower seven bits of the heading value are shown as "
                 "stored; 6 on most records. Records whose date fields are not a real date are "
                 "left out. The file states no time zone. An independent parse of the same "
                 "unit labels these times UTC, and that is not established here by other "
                 "means, so the time is written out as stored with no offset applied. Files "
                 "with identical content are read once and Identical Files gives how many "
                 "there were. A record states where the module's receiver placed itself at "
                 "that time. It does not establish who was in the vehicle.",
        "paths": ('*/obn/storage/gps*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/gps was zero bytes",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 12800 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/gps was zero bytes",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "obn/storage/gps was zero bytes",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "obn/storage/gps was zero bytes",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, obn/storage/gps was "
                             "zero bytes",
        },
        "output_types": "all",
        "artifact_icon": "navigation",
    },
    "gm_onstar_lg_nav_destinations": {
        "name": "GM OnStar LG Gen9 - Navigation Destinations",
        "description": "Destination lines from the telematics module's turn-by-turn navigation "
                       "log, with the log time and the latitude and longitude the line states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From the 'Dest lat' lines of obn/storage/flight, a text log of time-stamped "
                 "lines. Tested on four generation 9 units (a 2012 Chevrolet Cruze LT, a 2012 "
                 "GMC Acadia, a 2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave), read from "
                 "the file sets extracted from each unit's flash image. Only the Acadia held "
                 "data here; on the other three the file was present and zero bytes long, and "
                 "it is also zero bytes on the two tested generation 10 units. The Acadia's "
                 "log held 26 such lines. Each line gives the destination as two integers and, "
                 "in parentheses, the same position in decimal degrees; Latitude and Longitude "
                 "are the parenthesised values and the integers are kept in the as-stored "
                 "columns. The log is a fixed-size file that wraps, so the oldest lines have "
                 "been overwritten and rows are sorted by time. The file states no time zone. "
                 "An independent parse of the same unit labels these times UTC, and that is "
                 "not established here by other means, so the time is written out as stored "
                 "with no offset applied. Files with identical content are read once and "
                 "Identical Files gives how many there were. A row records that the module "
                 "logged a route to that destination at that time. It does not establish that "
                 "the vehicle arrived there.",
        "paths": ('*/obn/storage/flight*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/flight was zero bytes",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 26 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/flight was zero bytes",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "obn/storage/flight was zero bytes",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "obn/storage/flight was zero bytes",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, obn/storage/flight was "
                             "zero bytes",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "gm_onstar_lg_nav_guidance": {
        "name": "GM OnStar LG Gen9 - Navigation Guidance Prompts",
        "description": "Guidance prompt lines from the telematics module's turn-by-turn "
                       "navigation log, with the log time, the maneuver, the street named and "
                       "the distance text of each prompt.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From the 'VIAMOTOSendHMIData audio' lines of obn/storage/flight. Tested on "
                 "four generation 9 units (a 2012 Chevrolet Cruze LT, a 2012 GMC Acadia, a "
                 "2014 GMC Sierra 1500 SLE and a 2011 Buick Enclave), read from the file sets "
                 "extracted from each unit's flash image. Only the Acadia held data here; on "
                 "the other three the file was present and zero bytes long, and it is also "
                 "zero bytes on the two tested generation 10 units. The Acadia's log held 226 "
                 "such lines, with eleven maneuver texts such as TURN LEFT, EXIT/RAMP RIGHT "
                 "and DESTINATION AHEAD. Street is the text after 'street :' with %20 shown as "
                 "a space, and Distance Text is the rest of the line as logged. The numeric "
                 "prompt codes on the line are not surfaced. The log is a fixed-size file that "
                 "wraps, so the oldest lines have been overwritten and rows are sorted by "
                 "time. The file states no time zone. An independent parse of the same unit "
                 "labels these times UTC, and that is not established here by other means, so "
                 "the time is written out as stored with no offset applied. Files with "
                 "identical content are read once and Identical Files gives how many there "
                 "were. A row records that the module issued that prompt. It names a street on "
                 "the planned route and does not by itself place the vehicle on it; the GPS "
                 "Track artifact holds the positions. The log's other lines (events, settings, "
                 "network status) are not surfaced.",
        "paths": ('*/obn/storage/flight*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/flight was zero bytes",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 226 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, obn/storage/flight was zero bytes",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "obn/storage/flight was zero bytes",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "obn/storage/flight was zero bytes",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, obn/storage/flight was "
                             "zero bytes",
        },
        "output_types": "standard",
        "artifact_icon": "corner-up-right",
    },
    "gm_onstar_lg_embedded_phone_numbers": {
        "name": "GM OnStar LG Gen9 - Embedded Phone Stored Numbers",
        "description": "Phone numbers held in two fixed fields of the telematics module's "
                       "phone state file: one single-number field and one list of up to twenty "
                       "numbers.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "From var/sysinfo/phone.dat on generation 9, a fixed binary structure of "
                 "38,295 bytes that ends with the tag <SysInfo1.00>. The file has no internal "
                 "framing, so it is read only when it has exactly that size and tag, and a "
                 "field is reported only when it holds nothing but dialling characters up to "
                 "its first NUL. Tested on four generation 9 units read from their extracted "
                 "file sets. Two had this layout, a 2012 Chevrolet Cruze LT and a 2012 GMC "
                 "Acadia, and gave 2 and 10 rows; the other two carried a different size or "
                 "tag and are logged and not read. Two fields are reported: one single-number "
                 "field at offset 2468 and a list of 40-byte entries from offset 2514. What "
                 "the module uses each for is not established here. An independent parse of "
                 "the same two units listed every number of the list, 1 of 1 and 9 of 9, as a "
                 "phone number of the module's embedded phone, and that is the only evidence "
                 "of their role. Position is the entry's place in its field. Not reported from "
                 "the same file: ten numbers at offset 816, which that parse lists as the "
                 "service provider's own support numbers on both units, and seven short "
                 "service codes after them; both read as stock entries. Generation 10 keeps a "
                 "text phone.dat that the Stored Values artifact reads. Files with identical "
                 "content are read once and Identical Files gives how many there were. A row "
                 "records that the module's phone file held the number. It does not establish "
                 "that it was dialled.",
        "paths": ('*/var/sysinfo/phone.dat*',),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 2 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 10 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 0 "
                             "rows, phone.dat has a different size, not read",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 0 rows, "
                             "phone.dat has a different version tag, not read",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 0 rows, "
                             "phone.dat is the generation 10 text format",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 0 rows, phone.dat is the "
                             "generation 10 text format",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "gm_onstar_lg_unit_info": {
        "name": "GM OnStar LG - Unit Information",
        "description": "Identifiers and versions the telematics module stores: the VIN, the "
                       "device id, the assembly label code, the software version lines and the "
                       "network interface address.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM OnStar LG",
        "notes": "One row per value with the file it came from. Tested on four generation 9 "
                 "units: a 2012 Chevrolet Cruze LT, a 2012 GMC Acadia, a 2014 GMC Sierra 1500 "
                 "SLE and a 2011 Buick Enclave, read from the file sets extracted from each "
                 "unit's flash image. Tested on two generation 10 units: a 2016 Chevrolet "
                 "Cruze and a 2017 Buick Encore. Generation 9 gives the lines of var/ver.txt "
                 "and of the version file in var/fac that ver.txt names. Generation 10 gives "
                 "the lines of var/ver.txt, DevInfo/DevId, DevInfo/Ext/VIN, the VIN section of "
                 "vifdata.dat, the assembly label code of tcuid.dat and, where present, the "
                 "interface name and IP addresses in the keyval table of rr_db.dat (one unit). "
                 "The VIN is what the module stored, and a module moved between vehicles could "
                 "carry an earlier one. Generation 9 keeps its VIN in a binary vifdata.dat "
                 "that this module does not read. Values are reported as stored.",
        "paths": (
            '*/var/ver.txt*',
            '*/var/fac/ver_*.txt*',
            '*/DevInfo/DevId*',
            '*/DevInfo/Ext/VIN*',
            '*/var/sysinfo/vifdata.dat*',
            '*/var/sysinfo/tcuid.dat*',
            '*/var/sysinfo/rr_db.dat*',
        ),
        "sample_data": {
            "xtrmp_item020": "2012 Chevrolet Cruze LT, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item027": "2012 GMC Acadia, OnStar Gen9, extracted file set | 6 rows",
            "xtrmp_item030": "2014 GMC Sierra 1500 SLE, OnStar Gen9, extracted file set | 6 "
                             "rows",
            "xtrmp_item031": "2011 Buick Enclave, OnStar Gen9, extracted file set | 6 rows",
            "xtrmp_item081": "2016 Chevrolet Cruze, OnStar Gen10, extracted file set | 7 rows",
            "xtrmp_item115": "2017 Buick Encore, OnStar Gen10 | 9 rows",
        },
        "output_types": "standard",
        "artifact_icon": "info",
    },
}

_BT_FILE_SIZE = 323
_BT_SLOTS = 5
_BT_SLOT_SIZE = 60
_PB_FIELD_NAMES = ('Last Name', 'First Name', 'Home Number', 'Work Number',
                   'Mobile Number', 'Other Number')
_HEX_BYTES = re.compile(r'(?:[0-9A-Fa-f]{2} )*[0-9A-Fa-f]{2}')
_SECTION = re.compile(r'\[(.+)\]')
_POWER_LINE = re.compile(r'([A-Z][a-z]{2} [A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \d{4}),'
                         r'(-?\d+),(-?\d+)')
# Sections and keys of the generation 10 text files worth a row when they hold a value.
_STORED_KEYS = (
    ('RedialNum', 'PhoneNumber'), ('RecallNum', 'PhoneNumber'),
    ('NameTagList', 'NumOfNametag'), ('DestinationList', 'NumOfDestination'),
    ('IMSAPNLockOutInfo', 'LockOutCounter'),
    ('NAD', 'MDN'), ('NAD', 'MIN'), ('OBNDestContext', 'Latitude'),
    ('OBNDestContext', 'Longitude'), ('OBNDestContext', 'StreetNumber'),
    ('OBNDestContext', 'StreetText'), ('OBNDestContext', 'CrossStreetText'),
    ('OBNDestContext', 'POIText'), ('OBNRecentDestList', 'TotalDestListNum'),
    ('PacketInfo', 'DestLatitude'), ('PacketInfo', 'DestLongitude'),
    ('PacketInfo', 'DestURI'), ('TheftRecord', 'TheftActive'),
    ('OTUBMgmnt', 'ExpireYear'), ('OTUBMgmnt', 'ExpireMonth'),
    ('OTUBMgmnt', 'ExpireDay'), ('OTUBMgmnt', 'TotalUnits'),
    ('DEAMgmnt', 'Name'), ('DEAMgmnt', 'PhoneNum'), ('DEAMgmnt', 'Address'),
    ('DEAMgmnt', 'StreetName'), ('DEAMgmnt', 'CityName'), ('DEAMgmnt', 'State'),
)
# Numbered sections reported whole when present; none held rows on the tested units.
_LIST_SECTIONS = re.compile(r'^(OBNRecentDestList|NameTagList|DestinationList)\d+')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return b''


def _base_name(path):
    """The file name without the '(Deleted)' and '(CopyN)' marks an acquisition adds."""
    return re.sub(r'\((?:Deleted|Copy\d+)\)', '', os.path.basename(path))


def _distinct(paths):
    """(path, data, copies) for each distinct content among paths, in path order."""
    seen = {}
    for path in paths:
        data = _read(path)
        if not data:
            continue
        if data in seen:
            seen[data][1] += 1
        else:
            seen[data] = [path, 1]
    return [(path, data, copies) for data, (path, copies) in seen.items()]


def _address(raw):
    return ':'.join(f'{byte:02x}' for byte in raw)


# ---------------------------------------------------------------------------
# Generation 9: Bluetooth slots and phonebooks
# ---------------------------------------------------------------------------

def _parse_bt(data):
    """Slots of a BT.dat as (slot, device number, name, address), or None if unframed.

    The file is 323 bytes: an 8-byte header, five 60-byte slots and a '<SysInfo' tag.
    A slot stores the address as a four-byte lower part, a one-byte upper part and a
    two-byte non-significant part, big-endian, followed by a two-byte device number and
    the name.
    """
    tag_offset = 8 + _BT_SLOTS * _BT_SLOT_SIZE
    if len(data) != _BT_FILE_SIZE or not data[tag_offset:].startswith(b'<SysInfo'):
        return None
    slots = []
    for slot in range(_BT_SLOTS):
        record = data[8 + slot * _BT_SLOT_SIZE:8 + (slot + 1) * _BT_SLOT_SIZE]
        name = record[22:52].split(b'\x00', 1)[0].decode('utf-8', 'replace')
        number = struct.unpack('>H', record[20:22])[0]
        if not name and not number:
            continue
        address = record[18:20] + record[16:17] + record[13:16]
        slots.append((slot, number, name, _address(address)))
    return slots


@artifact_processor
def gm_onstar_lg_bt_devices(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'BT.dat']
    for file_found, data, copies in _distinct(files):
        slots = _parse_bt(data)
        if slots is None:
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} does not have the '
                    'Bluetooth slot layout, not read')
            continue
        source_paths.append(file_found)
        for slot, number, name, address in slots:
            data_list.append((number, name, address, slot, copies,
                              context.get_relative_path(file_found)))

    data_headers = ('Device Number', 'Device Name', 'Bluetooth Address', 'Slot',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _parse_pb(data):
    """(address, records) from a GMPB phonebook, or None when the framing does not hold.

    After a 16-byte header the file lists its fields (an id byte and a NUL-terminated
    name each), then records: a length byte followed by (field id, length, value)
    triples that must fill the record exactly.
    """
    if len(data) < 17 or data[:4] != b'GMPB':
        return None
    address = _address(data[6:12])
    offset = 17
    fields = {}
    try:
        for _ in range(data[16]):
            field_id = data[offset]
            end = data.index(b'\x00', offset + 1)
            fields[field_id] = data[offset + 1:end].decode('utf-8', 'replace')
            offset = end + 1
    except (IndexError, ValueError):
        return None
    if not fields:
        return None
    records = []
    while offset < len(data):
        length = data[offset]
        body = data[offset + 1:offset + 1 + length]
        if not length or len(body) != length:
            return None
        pos = 0
        record = {}
        while pos < length:
            if pos + 2 > length:
                return None
            field_id, size = body[pos], body[pos + 1]
            if field_id not in fields or pos + 2 + size > length:
                return None
            record.setdefault(fields[field_id], []).append(body[pos + 2:pos + 2 + size])
            pos += 2 + size
        records.append(record)
        offset += 1 + length
    return address, records


def _field(record, name):
    values = record.get(name, [])
    return '; '.join(value.decode('utf-8', 'replace') for value in values)


@artifact_processor
def gm_onstar_lg_phonebook(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context)
             if re.fullmatch(r'phone\d+\.pb', _base_name(f))]
    for file_found, data, copies in _distinct(files):
        parsed = _parse_pb(data)
        if parsed is None:
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} does not have the GMPB '
                    'framing, not read')
            continue
        source_paths.append(file_found)
        address, records = parsed
        number = int(re.search(r'phone(\d+)\.pb', _base_name(file_found)).group(1))
        for position, record in enumerate(records, start=1):
            data_list.append((number, address) + tuple(
                _field(record, name) for name in _PB_FIELD_NAMES) + (
                    position, copies, context.get_relative_path(file_found)))

    data_headers = ('Device Number', 'Handset Address', 'Last Name', 'First Name',
                    'Home Number', 'Work Number', 'Mobile Number', 'Other Number',
                    'Record Number',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Generation 10: sectioned text files
# ---------------------------------------------------------------------------

def _documents(data):
    """Every sectioned document inside a file, as (offset, {section: {key: value}}).

    A generation 10 state file is CRLF text that opens with a [*] section holding
    TimeStamp and Version and ends at a 0x1A byte. The extraction also holds 65,535-byte
    copies in which several such documents, of this file or another, follow one another
    after unrelated bytes. Each document is found by its [*] opening line and read up to
    its end byte or the next opening line; text with no TimeStamp is not a document.
    The module's raw flash image holds the same documents with no file system around
    them, including ones the file system has released, and is read the same way.
    """
    starts = [match.start() for match in re.finditer(rb'\[\*\]\r\n', data)]
    documents = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(data)
        chunk = data[start:end]
        stop = chunk.find(b'\x1a')
        if stop != -1:
            chunk = chunk[:stop]
        sections = {}
        name = None
        for line in chunk.decode('latin-1').split('\r\n'):
            match = _SECTION.fullmatch(line)
            if match:
                name = match.group(1)
                sections.setdefault(name, {})
            elif name is not None and '=' in line:
                key, value = line.split('=', 1)
                sections[name][key] = value
        if 'TimeStamp' in sections.get('*', {}):
            documents.append((start, sections))
    return documents


def _parse_sections(data):
    """The document a file opens with, or None when it does not open with one."""
    documents = _documents(data)
    if documents and documents[0][0] == 0:
        return documents[0][1]
    return None


def _save_time(sections):
    """The [*] TimeStamp ('MM-DD-YY HH:MM:SS') as 'YYYY-MM-DD HH:MM:SS', or ''."""
    try:
        return datetime.strptime(sections['*']['TimeStamp'].strip(),
                                 '%m-%d-%y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    except (KeyError, ValueError):
        return ''


def _hex_value(text):
    if _HEX_BYTES.fullmatch(text or ''):
        return bytes.fromhex(text.replace(' ', ''))
    return None


def _number(text, fmt):
    raw = _hex_value(text)
    if raw is None or len(raw) != struct.calcsize(fmt):
        return None
    return struct.unpack(fmt, raw)[0]


def _sectioned_documents(context):
    """(file, offset, sections) for every document in every distinct .dat file."""
    files = [f for f in _regular_files(context)
             if _base_name(f).endswith('.dat') or _base_name(f) == 'NORimage.bin']
    for file_found, data, _copies in _distinct(files):
        for offset, sections in _documents(data):
            yield file_found, offset, sections


@artifact_processor
def gm_onstar_lg_gps_reports(context):
    rows = {}
    source_paths = []
    for file_found, offset, sections in _sectioned_documents(context):
        for section, values in sections.items():
            index = re.fullmatch(r'GPSRegularReport(\d+)', section)
            if not index:
                continue
            latitude = _number(values.get('lat'), '<d')
            longitude = _number(values.get('lon'), '<d')
            if latitude is None or longitude is None or not (latitude or longitude):
                continue
            seconds = _number(values.get('utc_sec'), '<f')
            try:
                stamp = datetime(int(values['utc_year']), int(values['utc_month']),
                                 int(values['utc_day']), int(values['utc_hour']),
                                 int(values['utc_min']),
                                 int(seconds or 0)).strftime('%Y-%m-%d %H:%M:%S')
            except (KeyError, ValueError, OverflowError):
                stamp = ''
            row = (stamp, round(latitude / 1e7, 7), round(longitude / 1e7, 7),
                   values.get('elevation', ''), _number(values.get('sog'), '<f'),
                   _number(values.get('cog'), '<f'), _number(values.get('hdop'), '<f'),
                   values.get('sv_used_cnt', ''), values.get('gps_week', ''),
                   values.get('gps_tow', ''))
            if row in rows:
                rows[row][0] += 1
            else:
                rows[row] = [1, file_found, offset]
                if file_found not in source_paths:
                    source_paths.append(file_found)
    data_list = [row + (found[0], found[2], context.get_relative_path(found[1]))
                 for row, found in rows.items()]
    data_list.sort(key=lambda row: row[0], reverse=True)

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'Elevation (as stored)', 'Speed Over Ground (as stored)',
                    'Course Over Ground (as stored)', 'HDOP', 'Satellites Used',
                    'GPS Week', 'GPS Time Of Week (as stored)', 'Times Found',
                    'Document Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _display(value):
    """A stored value for display: hex byte strings become text when they are text."""
    raw = _hex_value(value)
    if raw is None or ' ' not in value:
        return value.strip()
    stripped = raw.rstrip(b'\x00')
    if not stripped:
        return ''
    try:
        text = stripped.decode('ascii')
    except UnicodeDecodeError:
        return value
    return text if text.isprintable() else value


@artifact_processor
def gm_onstar_lg_stored_values(context):
    rows = {}
    source_paths = []
    for file_found, offset, sections in _sectioned_documents(context):
        found = []
        for section, key in _STORED_KEYS:
            value = _display(sections.get(section, {}).get(key, ''))
            if value and value not in ('0', '-1'):
                found.append((section, key, value))
        for section, values in sections.items():
            if _LIST_SECTIONS.match(section):
                found.extend((section, key, _display(value))
                             for key, value in values.items() if _display(value))
        for section, key, value in found:
            row = (_save_time(sections), section, key, value)
            if row in rows:
                rows[row][0] += 1
            else:
                rows[row] = [1, file_found, offset]
                if file_found not in source_paths:
                    source_paths.append(file_found)
    data_list = [row + (found[0], found[2], context.get_relative_path(found[1]))
                 for row, found in rows.items()]

    data_headers = (('Document Save Time', 'datetime'), 'Section', 'Key', 'Value',
                    'Times Found', 'Document Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Generation 9: navigation position records and flight log
# ---------------------------------------------------------------------------

_GPS_RECORD = struct.Struct('>iiBBHHHBBBB')
_COORDINATE_UNITS = 6000000.0
_FLIGHT_LINE = re.compile(r'(\d{4})-(\d\d)-(\d\d):(\d\d)\.(\d\d)\.(\d\d)\.(\d{3}):([^\n]*)')
_FLIGHT_DEST = re.compile(r'^Dest lat (-?\d+) lon (-?\d+) \((-?[\d.]+),(-?[\d.]+)\)')
_FLIGHT_PROMPT = re.compile(r'^VIAMOTOSendHMIData audio (\d+) ([\d:]+) (.*?) street :(.*?) '
                            r'distance (.*)$')


def _gps_records(data):
    """Rows of an obn/storage/gps file, or None when it is not that layout.

    The file is a run of 20-byte big-endian records: latitude and longitude as integers
    of 1/6,000,000 degree, month, day, year, a speed value, a heading value, then hour,
    minute, second and one more byte. A record whose date fields are not a real date is
    left out, and the file is refused when more than half of them are.
    """
    if not data or len(data) % _GPS_RECORD.size:
        return None
    rows = []
    invalid = 0
    for offset in range(0, len(data), _GPS_RECORD.size):
        (latitude, longitude, month, day, year, speed, heading, hour, minute, second,
         _last) = _GPS_RECORD.unpack_from(data, offset)
        try:
            stamp = datetime(year, month, day, hour, minute, second)
        except ValueError:
            invalid += 1
            continue
        if not 2000 <= year <= 2100 or not (latitude or longitude):
            invalid += 1
            continue
        rows.append((stamp.strftime('%Y-%m-%d %H:%M:%S'),
                     round(latitude / _COORDINATE_UNITS, 7),
                     round(longitude / _COORDINATE_UNITS, 7),
                     round(speed * 0.0036, 1), heading >> 7, heading & 0x7f,
                     offset // _GPS_RECORD.size + 1))
    if invalid * 2 > len(data) // _GPS_RECORD.size:
        return None
    return rows


@artifact_processor
def gm_onstar_lg_gps_track(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'gps']
    for file_found, data, copies in _distinct(files):
        rows = _gps_records(data)
        if rows is None:
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} does not have the '
                    'position record layout, not read')
            continue
        if rows:
            source_paths.append(file_found)
        for row in rows:
            data_list.append(row + (copies, context.get_relative_path(file_found)))

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude', 'Speed (km/h)',
                    'Heading (degrees)', 'Low Heading Bits (as stored)', 'Record Number',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _flight_lines(data):
    for match in _FLIGHT_LINE.finditer(data.decode('latin-1')):
        year, month, day, hour, minute, second = (int(v) for v in match.groups()[:6])
        try:
            stamp = datetime(year, month, day, hour, minute,
                             second).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
        yield stamp, match.group(8).rstrip('\r')


@artifact_processor
def gm_onstar_lg_nav_destinations(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'flight']
    for file_found, data, copies in _distinct(files):
        found = False
        for stamp, text in _flight_lines(data):
            match = _FLIGHT_DEST.match(text)
            if not match:
                continue
            found = True
            data_list.append((stamp, float(match.group(3)), float(match.group(4)),
                              int(match.group(1)), int(match.group(2)), copies,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'Latitude (as stored)', 'Longitude (as stored)', 'Identical Files',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_onstar_lg_nav_guidance(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'flight']
    for file_found, data, copies in _distinct(files):
        found = False
        for stamp, text in _flight_lines(data):
            match = _FLIGHT_PROMPT.match(text)
            if not match:
                continue
            found = True
            street = match.group(4).replace('%20', ' ')
            data_list.append((stamp, match.group(3), street, match.group(5).strip(),
                              copies, context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Prompt Time', 'datetime'), 'Maneuver', 'Street', 'Distance Text',
                    'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

# ---------------------------------------------------------------------------
# Generation 9: the phone state file
# ---------------------------------------------------------------------------

_PHONE_FILE_SIZE = 38295
_PHONE_TAG_OFFSET = 38280
_PHONE_TAG = b'<SysInfo1.00>'
_PHONE_SINGLE_OFFSET = 2468
_PHONE_LIST_OFFSET = 2514
_PHONE_LIST_ENTRIES = 20
_PHONE_ENTRY_SIZE = 40
_DIAL_TEXT = re.compile(r'[0-9+*#]{1,32}')


def _phone_text(data, offset):
    text = data[offset:offset + 32].split(b'\x00', 1)[0].decode('latin-1')
    return text if _DIAL_TEXT.fullmatch(text) else ''


def _phone_numbers(data):
    """(field, position, number) rows of a generation 9 phone.dat, or None for another layout.

    The file is a fixed binary structure with no internal framing, so the layout is
    taken only for the one size and version tag it was worked out on. A field is
    reported only when it holds nothing but dialling characters up to its first NUL.
    """
    if len(data) != _PHONE_FILE_SIZE or \
            data[_PHONE_TAG_OFFSET:_PHONE_TAG_OFFSET + len(_PHONE_TAG)] != _PHONE_TAG:
        return None
    rows = []
    single = _phone_text(data, _PHONE_SINGLE_OFFSET)
    if single:
        rows.append(('Single number field', 1, single))
    for index in range(_PHONE_LIST_ENTRIES):
        number = _phone_text(data, _PHONE_LIST_OFFSET + _PHONE_ENTRY_SIZE * index)
        if number:
            rows.append(('Number list', index + 1, number))
    return rows


@artifact_processor
def gm_onstar_lg_embedded_phone_numbers(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'phone.dat']
    for file_found, data, copies in _distinct(files):
        if data.startswith(b'[*]\r\n'):
            continue
        rows = _phone_numbers(data)
        if rows is None:
            # Only a file carrying the generation 9 tag is worth a line in the log.
            if b'<SysInfo' not in data[-32:]:
                continue
            logfunc(f'GM OnStar LG: {os.path.basename(file_found)} ({len(data)} bytes) is not '
                    'the phone file layout this reader knows, not read')
            continue
        if rows:
            source_paths.append(file_found)
        for field, position, number in rows:
            data_list.append((field, position, number, copies,
                              context.get_relative_path(file_found)))

    data_headers = ('Field', 'Position', 'Phone Number', 'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Both generations
# ---------------------------------------------------------------------------

@artifact_processor
def gm_onstar_lg_power_off_log(context):
    data_list = []
    source_paths = []
    files = [f for f in _regular_files(context) if _base_name(f) == 'poweroff.log']
    for file_found, data, copies in _distinct(files):
        found = False
        for match in _POWER_LINE.finditer(data.decode('latin-1')):
            try:
                stamp = datetime.strptime(' '.join(match.group(1).split()),
                                          '%a %b %d %H:%M:%S %Y')
            except ValueError:
                continue
            found = True
            data_list.append((stamp.strftime('%Y-%m-%d %H:%M:%S'), int(match.group(2)),
                              int(match.group(3)), copies,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Power Off Time', 'datetime'), 'Second Field (as stored)',
                    'Third Field (as stored)', 'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_onstar_lg_unit_info(context):
    data_list = []
    source_paths = []

    def add(label, value, file_found):
        value = str(value).strip().strip('\x00')
        if not value:
            return
        relative = context.get_relative_path(file_found)
        data_list.append((label, value, relative))
        if file_found not in source_paths:
            source_paths.append(file_found)
        device_info('GM OnStar LG', label, value, relative)

    groups = {}
    for file_found in _regular_files(context):
        groups.setdefault(_base_name(file_found), []).append(file_found)
    # ver.txt can hold the path of the version file in var/fac that is in effect.
    named = set()
    for file_found in groups.get('ver.txt', []):
        named.update(re.findall(r'ver_\w+\.txt', _read(file_found).decode('latin-1')))
    for base, files in sorted(groups.items()):
        if base == 'rr_db.dat':
            for file_found in files:
                if _read(file_found)[:16] != b'SQLite format 3\x00':
                    continue
                db = open_sqlite_db_readonly(file_found)
                if db is None:
                    continue
                try:
                    rows = db.execute("SELECT key, value FROM keyval WHERE key IN "
                                      "('IFNAME', 'IP4ADDR', 'IP6ADDR')").fetchall()
                except sqlite3.Error:
                    rows = []
                db.close()
                for key, value in rows:
                    add(f'Network {key}', value or '', file_found)
            continue
        for file_found, data, _copies in _distinct(files):
            if base == 'ver.txt' or base in named:
                for line in data.decode('latin-1').splitlines():
                    add(f'Version File Line ({base})', line, file_found)
            elif base == 'DevId':
                add('Device ID', data.decode('latin-1'), file_found)
            elif base == 'VIN':
                add('VIN (DevInfo)', data.decode('latin-1'), file_found)
            elif base in ('vifdata.dat', 'tcuid.dat'):
                sections = _parse_sections(data)
                if sections is None:
                    continue
                if base == 'vifdata.dat':
                    add('VIN (vifdata)', _display(sections.get('VIN', {}).get('VIN', '')),
                        file_found)
                else:
                    add('Assembly Label Code',
                        sections.get('TcuID', {}).get('AssyLabel.Code', ''), file_found)

    data_headers = ('Property', 'Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
