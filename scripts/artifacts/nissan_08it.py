"""Nissan 08IT infotainment head unit (hard-disk navigation unit), generations 3000 and 8000.

Named for the module: the vehicle model behind each tested unit is not recorded, so the
module name is the only identity these files share. The telephone data sits in fixed-size
binary records under a TEL folder, keyed by the handset's Bluetooth address in the file
name:

    TEL/CALLLOGS/f_incoming<address>.txt, f_outgoing..., f_miss...   call lists
    TEL/HF_MEMORY/f_hf_memory<address>.txt                           the handset phonebook
    TEL/INFO/f_info.txt or f_phonebookinfo.txt                       the device table
    USER/DEBUG/LOC/LOC_DS<n>.log                                     compressed position logs
    USER/USBA/file.lst (also USBV, DATACD)                           names of media files
    USER/CLIB/cl.dtb.bak                                             the music library
    USER/CUSTOM/ccu.edb, sccu.edb                                    disc and track titles

The two generations use different record layouts for the same files. Each reader picks
the layout from the file's own size and record markers and gives the file up, with a log
line, when neither fits.
"""

import hashlib
import os
import re
import struct
import zlib
from datetime import datetime

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "nissan_08it_call_logs": {
        "name": "Nissan 08IT - Call Logs",
        "description": "Entries of the incoming, outgoing and missed call files the head unit "
                       "keeps for each handset, with the call clock reading, the phone number "
                       "and, on generation 8000, the name stored in each entry.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/CALLLOGS/f_incoming<address>.txt, f_outgoing<address>.txt and "
                 "f_miss<address>.txt. Despite the extension they are binary files of "
                 "fixed-size records after a four-byte count. Tested on two units, one of "
                 "generation 3000 and one of generation 8000, read from the file sets "
                 "extracted from each unit's hard disk; the vehicle model behind each is not "
                 "recorded. Call List is taken from the file name. Handset Address is the "
                 "twelve hex digits in the file name, shown with colons. Generation 3000 "
                 "stores 102-byte records with an ASCII number and a big-endian date; "
                 "generation 8000 stores 192-byte records with a UTF-16 name, an ASCII number "
                 "and a little-endian date, and marks each used record with fixed bytes. The "
                 "layout is chosen from the file size and those marks, Record Layout says "
                 "which was used, and a file that fits neither is logged and not read. Only "
                 "the number of records the count states is read. The generation 3000 unit "
                 "held one incoming file of 20 entries, and for the two entries compared an "
                 "independent parse of the same file gave the same times and the same list. "
                 "The generation 8000 unit held 15 files for five handsets, with 32 entries in "
                 "four of them. The record holds no time zone, so the time is the unit's clock "
                 "reading, written out as if it were UTC with no offset applied. Record Value "
                 "is the byte after the date on generation 3000 and the four-byte value before "
                 "it on generation 8000; nothing available here documents either. Name is "
                 "empty on generation 3000 because its record has no name field. An entry "
                 "records that the unit held this call list entry for the handset. It does not "
                 "establish who used the handset.",
        "paths": ('*/TEL/CALLLOGS/f_*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 20 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 32 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "nissan_08it_phone_memory": {
        "name": "Nissan 08IT - Handset Phonebook",
        "description": "Entries of the phonebook file the head unit keeps for each handset, "
                       "with the name and the phone numbers stored in each entry.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/HF_MEMORY/f_hf_memory<address>.txt on generation 8000, a binary "
                 "file of 384-byte records after a four-byte count: an index, a UTF-16 name "
                 "and five number slots, each an ASCII number with a four-byte value. Tested "
                 "on two units, one of generation 3000 and one of generation 8000, read from "
                 "the file sets extracted from each unit's hard disk; the vehicle model behind "
                 "each is not recorded. The generation 8000 unit held five such files, one per "
                 "handset; one held 270 entries and four held none. The generation 3000 unit "
                 "had no HF_MEMORY folder in its extracted set. A file whose size or record "
                 "marks do not fit is logged and not read. Number Values are the four-byte "
                 "value of each number slot, in the same order as Phone Numbers; 2, 3 and 9 "
                 "occur and nothing available here documents them. Handset Address is the "
                 "twelve hex digits in the file name, shown with colons. An entry records that "
                 "the unit held the contact for that handset. It does not establish that any "
                 "number was dialled.",
        "paths": ('*/TEL/HF_MEMORY/f_hf_memory*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "HF_MEMORY folder in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 270 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "nissan_08it_devices": {
        "name": "Nissan 08IT - Bluetooth Device Table",
        "description": "Slots of the head unit's Bluetooth device table, with the handset "
                       "address stored in each occupied slot and, on generation 8000, the "
                       "device name.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From TEL/INFO/f_info.txt on generation 8000 (164-byte slots holding an "
                 "address and a name) and TEL/INFO/f_phonebookinfo.txt on generation 3000 "
                 "(104-byte slots holding an address). Tested on two units, one of generation "
                 "3000 and one of generation 8000, read from the file sets extracted from each "
                 "unit's hard disk; the vehicle model behind each is not recorded. Each held "
                 "five slots, with five occupied on generation 8000 and four on generation "
                 "3000. The address is stored as twelve ASCII hex digits and is shown with "
                 "colons when all twelve are present. On the generation 3000 unit three of the "
                 "four addresses had a NUL byte in place of their first digit; those are shown "
                 "with a question mark in that position and without colons, and what the NUL "
                 "means is not established here. The rest of each slot is not decoded. A slot "
                 "records that the unit held an entry for the device. It does not establish "
                 "who carried it. Not read from the same units: the voice tag and learning "
                 "files. The navigation backup files under BUP are read by the Navigation "
                 "Backup Records artifact.",
        "paths": ('*/TEL/INFO/f_info.txt*', '*/TEL/INFO/f_phonebookinfo.txt*'),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 4 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 5 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "nissan_08it_gps_track": {
        "name": "Nissan 08IT - GPS Track",
        "description": "Position records from the head unit's compressed location logs, one "
                       "per second while a log was being written, with the time, latitude and "
                       "longitude of each record.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From USER/DEBUG/LOC/LOC_DS<n>.log. Each file is a run of blocks, a two-byte "
                 "value followed by a zlib stream that inflates to 2,048 bytes, and the "
                 "inflated content holds the unit's positioning records. Tested on one "
                 "generation 8000 unit, which held 140 such files; the tested generation 3000 "
                 "unit had no DEBUG folder in its extracted set. A position record is found by "
                 "its marker (the byte 0xA0, one varying byte and three zero bytes) and holds "
                 "latitude and longitude in 1/60,000 degree, two more values, and a two-digit "
                 "year, month, day, hour, minute and second. The outer framing of the log's "
                 "records is not known, so a candidate is kept only when its coordinates are "
                 "in range and its date fields form a real date; on the tested unit 23 "
                 "candidates failed that test and are counted in the run log. The unit gave "
                 "159,085 records, one per second, dated from 9 to 28 November 2020. The "
                 "decoding was checked by comparison: an independent parse of the same unit "
                 "listed 159,144 track points, 159,084 of them share a timestamp with a record "
                 "read here, and on every one of those the position agreed to within 0.000002 "
                 "degree. Sixty of its points are not reached here and one record here is not "
                 "in it. Reading stops at the first block that does not inflate, which left "
                 "173,064 bytes unread across the 140 files. The record states no time zone. "
                 "The independent parse labels these times UTC and that is not established "
                 "here by other means, so the time is written out as stored with no offset "
                 "applied. First Value and Second Value are the four-byte and two-byte values "
                 "after the longitude, and Marker Byte is the varying byte of the marker; all "
                 "three are shown as stored because nothing available here documents them. The "
                 "rest of each record, and the log's other record types, are not decoded. Rows "
                 "are sorted by time and Log File names the file each came from. A record "
                 "states where the unit's positioning placed the vehicle at that time. It does "
                 "not establish who was in it.",
        "paths": ('*/DEBUG/LOC/LOC_DS*.log*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "DEBUG/LOC folder in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 159085 rows",
        },
        "output_types": "all",
        "artifact_icon": "navigation",
    },
    "nissan_08it_gps_logs": {
        "name": "Nissan 08IT - GPS Log Summary",
        "description": "One row per compressed location log, with the time and position of its "
                       "first and last position record and the number of position records it "
                       "holds.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "A summary of the GPS Track artifact, one row for each log file that held "
                 "position records. From USER/DEBUG/LOC/LOC_DS<n>.log. Each file is a run of "
                 "blocks, a two-byte value followed by a zlib stream that inflates to 2,048 "
                 "bytes, and the inflated content holds the unit's positioning records. Tested "
                 "on one generation 8000 unit, which held 140 such files; the tested "
                 "generation 3000 unit had no DEBUG folder in its extracted set. A position "
                 "record is found by its marker (the byte 0xA0, one varying byte and three "
                 "zero bytes) and holds latitude and longitude in 1/60,000 degree, two more "
                 "values, and a two-digit year, month, day, hour, minute and second. The outer "
                 "framing of the log's records is not known, so a candidate is kept only when "
                 "its coordinates are in range and its date fields form a real date; on the "
                 "tested unit 23 candidates failed that test and are counted in the run log. "
                 "139 of the 140 files held position records. The record states no time zone. "
                 "The independent parse labels these times UTC and that is not established "
                 "here by other means, so the time is written out as stored with no offset "
                 "applied. The first and last record of a file bound one stretch of recording. "
                 "That a file is one journey is the natural reading and is not established "
                 "here.",
        "paths": ('*/DEBUG/LOC/LOC_DS*.log*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "DEBUG/LOC folder in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 139 rows",
        },
        "output_types": "standard",
        "artifact_icon": "list",
    },
    "nissan_08it_media_file_list": {
        "name": "Nissan 08IT - Media File List",
        "description": "File names in the fixed-record media file lists the unit keeps under "
                       "its USBA, USBV and DATACD folders, with each name's position and the "
                       "number stored after it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From USER/USBA/file.lst, USER/USBV/file.lst and USER/DATACD/file.lst. The "
                 "layout was worked out from the files: 5,000 records of 260 bytes, each a "
                 "256-byte name field padded with NUL and four more bytes, with the used "
                 "records first. A file that does not fit that is logged and not read. Tested "
                 "on one generation 8000 unit read from its extracted file set: the USBA list "
                 "held 869 names, 868 of them distinct, with audio file extensions, and the "
                 "USBV and DATACD lists were all zeros. A tested generation 3000 unit has none "
                 "of the three files. That USBA, USBV and DATACD stand for USB audio, USB "
                 "video and data disc is a reading of the folder names and of the extensions "
                 "seen, not something documented here. Names carry no folder path. Trailing "
                 "Number is the four bytes after the name read as a little-endian number; it "
                 "ran from 0 to 254 and was not zero on 652 rows, and what it stands for is "
                 "not established. The list holds no time. A row records that the unit listed "
                 "a file of that name. It does not establish that the file was played.",
        "paths": ('*/USBA/file.lst*', '*/USBV/file.lst*', '*/DATACD/file.lst*'),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "file.lst in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 869 rows",
        },
        "output_types": "standard",
        "artifact_icon": "music",
    },
    "nissan_08it_music_library": {
        "name": "Nissan 08IT - Music Library Tracks",
        "description": "Track records of the unit's music library file: the title, the path of "
                       "the audio file on the hard disk, a stored date and time and a second "
                       "stored date with the number that follows it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From USER/CLIB/cl.dtb.bak. The layout was worked out from the file. A track "
                 "record starts with the path of its audio file, /ALBUM/<fourteen "
                 "digits>/<nn>.SCD, with the title 32 bytes after it and two date fields "
                 "further on. Records are not contiguous, so each one is located by that path "
                 "and the rest is read at fixed distances from it. Tested on one generation "
                 "3000 unit read from its extracted file set: 136 records were found, the same "
                 "number the file states at offset 12, and a difference is logged. A tested "
                 "generation 8000 unit has no such file. Stored Date And Time is seven bytes, "
                 "year first; on all 136 records its date equals the date in the fourteen "
                 "digits of the folder name, which is consistent with the time the track was "
                 "stored on the disk, and the tested values run from 2010 to 2016. Other "
                 "Stored Date has no time of day. It was empty on 14 records and on the other "
                 "122 it was on or after the first date, with values from 2010 to 2020; the "
                 "number after it was 0 on exactly those 14 and from 1 to 179 on the rest. "
                 "That pattern fits a last-played date and a play count, but nothing available "
                 "here documents it, so both are left unlabelled. Dates are the unit's own "
                 "clock with no zone and are shown as stored. The album name records in the "
                 "same file are read by the Music Library Albums artifact; a track is tied to "
                 "an album through the date in its folder name. The audio files themselves are "
                 "not in the extracted set.",
        "paths": ('*/USER/CLIB/cl.dtb*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 136 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 0 rows, no "
                             "CLIB folder in the extracted set",
        },
        "output_types": "standard",
        "artifact_icon": "disc",
    },
    "nissan_08it_music_library_albums": {
        "name": "Nissan 08IT - Music Library Albums",
        "description": "Album records of the unit's music library file: the album name, a "
                       "stored date and time and the count the record stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From USER/CLIB/cl.dtb.bak. The layout was worked out from the file: the "
                 "32-bit number at the start is the number of album records, and they are 920 "
                 "bytes each from offset 0x4a0 with a name, a count and seven bytes of date "
                 "and time, year first. A file where any of those records does not hold a "
                 "valid date and time is logged and not read. Tested on one generation 3000 "
                 "unit read from its extracted file set, which gave 10 rows; a tested "
                 "generation 8000 unit has no such file. Each album's stored date is the date "
                 "of one track folder in the Music Library Tracks artifact, and its time is "
                 "from 10 to 75 seconds after the time in that folder's name, which is how an "
                 "album is tied to its tracks here; no stored link between the two records was "
                 "worked out. Three of the ten names were a date and time text and two began "
                 "with Unknown, which reads as a default name where none was known. Stored "
                 "Count is the number at offset 0x100 of the record. On nine albums it was one "
                 "more than the number of track records in the matching folder and on the "
                 "tenth it was 17 against 5 track records; what it counts is not established. "
                 "Dates are the unit's own clock with no zone and are shown as stored.",
        "paths": ('*/USER/CLIB/cl.dtb*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 10 rows",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 0 rows, no "
                             "CLIB folder in the extracted set",
        },
        "output_types": "standard",
        "artifact_icon": "disc",
    },
    "nissan_08it_disc_titles": {
        "name": "Nissan 08IT - Disc Title Records",
        "description": "Disc records of the unit's title store: the album, album artist and "
                       "year stored for a disc and the title and artist stored for each of its "
                       "tracks.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From USER/CUSTOM/ccu.edb and sccu.edb, files that start with the text "
                 "XANAVI06IT. The layout was worked out from the files. A disc record holds a "
                 "table of numbers and then its text as values each stored as a 32-bit length "
                 "and that many bytes: nine values for the disc, then six for each track. A "
                 "record is taken only when all of those can be read, the track count is a "
                 "number from 1 to 99, the 16-bit number at offset 0x1c of the record is that "
                 "count plus one, and the names decode as UTF-8. Tested on one generation 8000 "
                 "unit read from its extracted file set: each of the two files held the same "
                 "five disc records with 50 tracks between them, so the artifact gave 100 "
                 "rows, 50 a file. A tested generation 3000 unit has neither file. What sets "
                 "the two files apart is not established. Year is the stored text and was "
                 "empty on two of the five discs. Track Artist was filled on 25 of the 50 "
                 "tracks, some on every disc. Each name is also stored a second time in "
                 "another script, and each disc and track carries an identifier and a "
                 "32-character value; those are not surfaced. The record holds no time. A row "
                 "records that the unit stored those titles for a disc. It does not establish "
                 "when the disc was in the unit or that it was played.",
        "paths": ('*/USER/CUSTOM/*.edb*',),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, no "
                             "CUSTOM folder in the extracted set",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 100 rows",
        },
        "output_types": "standard",
        "artifact_icon": "disc",
    },
    "nissan_08it_navigation_backup_records": {
        "name": "Nissan 08IT - Navigation Backup Records",
        "description": "Named records of the unit's navigation backup files: the text stored "
                       "in each record, which on the tested unit read as place names and "
                       "street addresses, the date the record carries, and three numeric "
                       "fields of the record, shown as stored, whose meaning is not "
                       "established.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-10",
        "last_update_date": "2026-10-10",
        "requirements": "none",
        "category": "Nissan 08IT",
        "notes": "From BUP/BACKUP.CUR and BACKUP.PRE. On the tested units the files read are "
                 "1,048,576 bytes and start with the text NEPO. The layout was worked out from "
                 "the files. Records are 268 bytes: a text field of up to 32 UTF-16 characters "
                 "at the start, a second text field at offset 64, a date at offset 0x70 stored "
                 "as a 16-bit year, a month and a day, sixteen marker bytes at offset 0x8c, "
                 "and at offset 0x9c a 32-bit value and two 16-bit values, read little-endian "
                 "and shown in the three Value At columns, the first as eight hexadecimal "
                 "digits; nothing available here documents them. A record is taken where the "
                 "marker bytes stand at their place and the first text field holds printable "
                 "text and the date field holds a calendar date or zeros; the run log counts "
                 "the marked records with no text. Tested on one generation 8000 unit read "
                 "from its extracted file set: each of the two files held 353 marked records, "
                 "16 with text and 337 without, and the 16 were the same in both files, so the "
                 "artifact gave 32 rows, 16 a file. On the tested generation 3000 unit the two "
                 "files start with OPEN, the same four letters in the opposite order, and hold "
                 "36 bytes that are not zero. A file with the same content also sits in one "
                 "acquisition folder of the generation 8000 unit. OPEN files are logged and "
                 "not read, so the generation 3000 unit gave no rows and the layout is "
                 "untested on that generation. On the tested rows Text read as a place name or "
                 "a street address with a town, and Second Text, filled on 9 of the 16, as a "
                 "short region code or a second name. Date In Record is the stored year, month "
                 "and day, written out as stored; 14 of the 16 records carried one, from 2017 "
                 "to 2019, and 2 held zeros and show none. What the date marks, such as when "
                 "the place was stored or last used, is not established here, and neither is "
                 "which list each record belongs to: 14 sat in one run of records and the "
                 "other 2 each in a separate shorter run earlier in the file. The three values "
                 "look like a position on a map grid and are not decoded into latitude and "
                 "longitude. Three records held all ones in the first with the other two at "
                 "the largest positive signed 16-bit value. An independent parse of the same "
                 "unit listed 16 locations with coordinates, and the part of Text before its "
                 "first comma appears in it for 11 of the 16 records here; no way to turn the "
                 "stored fields into those coordinates was found here, so no position is "
                 "derived. Two copies of each file under a ~ENTR~01 folder, and a third "
                 "acquisition folder's pair, one starting with OPEN and one all zeros, do not "
                 "start with NEPO and are logged and not read. Files with identical content "
                 "are read once and Identical Files gives how many there were; it held one "
                 "value, 2, on all 32 rows: two of the unit's three acquisition folders hold "
                 "the same pair of files. Not read from the same files: a run of 52 records of "
                 "332 bytes from offset 0x1f8, each starting with a text field. They held 16 "
                 "distinct texts, one of them on 32 of the 52 records, no marker bytes and no "
                 "date were found in them, and which list they are is not established. A row "
                 "records that the unit's navigation backup held that entry. It does not "
                 "establish that the vehicle went there.",
        "paths": ('*/BUP/*BACKUP.CUR*', '*/BUP/*BACKUP.PRE*'),
        "sample_data": {
            "xtrmp_item057": "Nissan 08IT generation 3000, extracted file set | 0 rows, "
                             "the backup files start with OPEN and are not read",
            "xtrmp_item059": "Nissan 08IT generation 8000, extracted file set | 32 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
}

# The call list files name their own list.
_CALL_FILES = (('f_incoming', 'Incoming'), ('f_outgoing', 'Outgoing'), ('f_miss', 'Missed'))
_TEXT_MARK = bytes.fromhex('0b010200')
_NUMBER_MARK = bytes.fromhex('0300ff80')
_HEX12 = re.compile(r'[0-9A-Fa-f]{12}')


def _regular_files(context):
    return sorted({str(f) for f in context.get_files_found() if not os.path.isdir(str(f))})


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return b''


def _address(text):
    if _HEX12.fullmatch(text or ''):
        return ':'.join(text[i:i + 2] for i in range(0, 12, 2)).lower()
    return text or ''


def _address_from_name(path, prefix):
    match = _HEX12.match(os.path.basename(path)[len(prefix):])
    return _address(match.group(0)) if match else ''


def _ascii(raw):
    return raw.split(b'\x00', 1)[0].decode('latin-1')


def _wide_be(raw):
    """A NUL-terminated UTF-16 big-endian string from a fixed field."""
    raw = raw[:len(raw) - len(raw) % 2]
    for index in range(0, len(raw), 2):
        if raw[index:index + 2] == b'\x00\x00':
            raw = raw[:index]
            break
    return raw.decode('utf-16-be', 'replace')


def _stamp(year, month, day, hour, minute, second):
    try:
        return datetime(year, month, day, hour, minute, second).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


# ---------------------------------------------------------------------------
# Call logs
# ---------------------------------------------------------------------------

def _calls_3000(data):
    """Generation 3000: a big-endian count, then 102-byte records of an ASCII number
    and a seven-field big-endian date."""
    body = len(data) - 4
    if body <= 0 or body % 102:
        return None
    count = struct.unpack('>I', data[:4])[0]
    if count > body // 102:
        return None
    rows = []
    for index in range(count):
        record = data[4 + 102 * index:4 + 102 * (index + 1)]
        year, month, day, hour, minute, second, last = struct.unpack('>HBBBBBB',
                                                                     record[94:102])
        rows.append((_stamp(year, month, day, hour, minute, second), '',
                     _ascii(record[:94]), last, index + 1))
    return rows


def _calls_8000(data):
    """Generation 8000: a little-endian count, then 192-byte records holding a UTF-16
    name, an ASCII number, a four-byte value and a little-endian date. Each used record
    carries fixed marker bytes, which is what tells this layout from the other."""
    body = len(data) - 4
    if body <= 0 or body % 192:
        return None
    count = struct.unpack('<I', data[:4])[0]
    if count > body // 192:
        return None
    rows = []
    for index in range(count):
        record = data[4 + 192 * index:4 + 192 * (index + 1)]
        if record[0x40:0x44] != _TEXT_MARK or record[0xb0:0xb4] != _NUMBER_MARK:
            return None
        year, month, day, hour, minute, second, _last = struct.unpack('<HBBBBBB',
                                                                      record[0xb8:0xc0])
        rows.append((_stamp(year, month, day, hour, minute, second),
                     _wide_be(record[0:0x40]), _ascii(record[0x88:0xb0]),
                     struct.unpack('<I', record[0xb4:0xb8])[0], index + 1))
    return rows


@artifact_processor
def nissan_08it_call_logs(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        kind = next(((prefix, label) for prefix, label in _CALL_FILES
                     if base.startswith(prefix)), None)
        if kind is None:
            continue
        data = _read(file_found)
        rows = _calls_8000(data)
        layout = '8000'
        if rows is None:
            rows = _calls_3000(data)
            layout = '3000'
        if rows is None:
            logfunc(f'Nissan 08IT call logs: {base} ({len(data)} bytes) fits neither record '
                    'layout, not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, kind[0])
        for stamp, name, number, value, position in rows:
            data_list.append((stamp, kind[1], name, number, value, position, address,
                              layout, context.get_relative_path(file_found)))

    data_headers = (('Call Time', 'datetime'), 'Call List', 'Name', 'Phone Number',
                    'Record Value (as stored)', 'Position In File', 'Handset Address',
                    'Record Layout', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Handset phonebook
# ---------------------------------------------------------------------------

def _phone_memory(data):
    """Generation 8000 phonebook: a little-endian count, then 384-byte records holding
    an index, a UTF-16 name and five number slots, each slot an ASCII number, a marker
    and a four-byte value."""
    body = len(data) - 4
    if body <= 0 or body % 384:
        return None
    count = struct.unpack('<I', data[:4])[0]
    if count > body // 384:
        return None
    rows = []
    for position in range(count):
        record = data[4 + 384 * position:4 + 384 * (position + 1)]
        if record[0x48:0x4c] != _TEXT_MARK or record[0xb8:0xbc] != _NUMBER_MARK:
            return None
        numbers = []
        values = []
        for slot in range(5):
            start = 0x90 + 48 * slot
            number = _ascii(record[start:start + 40])
            if number:
                numbers.append(number)
                values.append(str(struct.unpack('<I', record[start + 44:start + 48])[0]))
        rows.append((_wide_be(record[0x08:0x48]), '; '.join(numbers), '; '.join(values),
                     struct.unpack('<I', record[:4])[0], position + 1))
    return rows


@artifact_processor
def nissan_08it_phone_memory(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if not base.startswith('f_hf_memory'):
            continue
        data = _read(file_found)
        rows = _phone_memory(data)
        if rows is None:
            logfunc(f'Nissan 08IT phonebook: {base} ({len(data)} bytes) does not fit the '
                    'record layout, not read')
            continue
        source_paths.append(file_found)
        address = _address_from_name(file_found, 'f_hf_memory')
        for name, numbers, values, index, position in rows:
            data_list.append((address, name, numbers, values, index, position,
                              context.get_relative_path(file_found)))

    data_headers = ('Handset Address', 'Name', 'Phone Numbers', 'Number Values (as stored)',
                    'Entry Index', 'Position In File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Device table
# ---------------------------------------------------------------------------

@artifact_processor
def nissan_08it_devices(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        data = _read(file_found)
        if base.startswith('f_info.txt'):
            size, layout = 164, '8000'
        elif base.startswith('f_phonebookinfo.txt'):
            size, layout = 104, '3000'
        else:
            continue
        if not data or len(data) % size:
            logfunc(f'Nissan 08IT devices: {base} ({len(data)} bytes) is not a whole number '
                    f'of {size}-byte slots, not read')
            continue
        found = False
        for slot in range(len(data) // size):
            record = data[slot * size:(slot + 1) * size]
            if not any(record[:16]):
                continue
            # A slot whose first address character is NUL keeps the other eleven.
            address = record[:12].replace(b'\x00', b'?').decode('latin-1')
            name = _ascii(record[0x40:0x60]) if layout == '8000' else ''
            found = True
            data_list.append((slot + 1, _address(address), name, layout,
                              context.get_relative_path(file_found)))
        if found:
            source_paths.append(file_found)

    data_headers = ('Slot', 'Handset Address (as stored)', 'Device Name', 'Record Layout',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Location debug logs
# ---------------------------------------------------------------------------

_POSITION = struct.Struct('<iiiH6H')
_MINUTE_UNITS = 60000.0


def _inflate_blocks(data):
    """The decompressed content of a LOC_DS log and the bytes left unread at its end.

    The file is a run of blocks, each a two-byte value followed by a zlib stream. Reading
    stops at the first position that does not hold a stream.
    """
    blocks = []
    offset = 0
    while offset + 4 <= len(data) and data[offset + 2:offset + 4] == b'\x78\x9c':
        inflater = zlib.decompressobj()
        try:
            blocks.append(inflater.decompress(data[offset + 2:]))
        except zlib.error:
            break
        offset = len(data) - len(inflater.unused_data)
    return b''.join(blocks), len(data) - offset


def _positions(content):
    """Dated position records in decompressed log content, and how many candidates failed.

    A record is the byte 0xA0, one varying byte and three zero bytes, followed by
    latitude and longitude in 1/60,000 degree, two more values and a
    two-digit year, month, day, hour, minute and second, all little-endian. The log's
    outer record framing is not known, so a candidate is kept only when its coordinates
    are in range and its six date fields form a real date.
    """
    rows = []
    rejected = 0
    index = content.find(b'\xa0')
    while index != -1:
        if content[index + 2:index + 5] == b'\x00\x00\x00' and \
                index + 5 + _POSITION.size <= len(content):
            (latitude, longitude, altitude, value, year, month, day, hour, minute,
             second) = _POSITION.unpack_from(content, index + 5)
            stamp = ''
            if year < 100 and abs(latitude) <= 90 * 60000 and \
                    abs(longitude) <= 180 * 60000 and (latitude or longitude):
                stamp = _stamp(2000 + year, month, day, hour, minute, second)
            if stamp:
                rows.append((stamp, round(latitude / _MINUTE_UNITS, 6),
                             round(longitude / _MINUTE_UNITS, 6), altitude, value,
                             content[index + 1]))
            else:
                rejected += 1
        index = content.find(b'\xa0', index + 1)
    return rows, rejected


def _location_logs(context):
    """(file, rows) for each distinct LOC_DS log, with what was skipped written to the log."""
    seen = set()
    for file_found in _regular_files(context):
        base = os.path.basename(file_found)
        if not re.match(r'LOC_DS\d+\.log', base):
            continue
        data = _read(file_found)
        if not data or data in seen:
            continue
        seen.add(data)
        content, unread = _inflate_blocks(data)
        rows, rejected = _positions(content)
        if unread or rejected:
            logfunc(f'Nissan 08IT location log {base}: {unread} bytes after the last '
                    f'readable block, {rejected} candidate records failed validation')
        if rows:
            yield file_found, rows


@artifact_processor
def nissan_08it_gps_track(context):
    data_list = []
    source_paths = []
    for file_found, rows in _location_logs(context):
        source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        base = os.path.basename(file_found)
        for row in rows:
            data_list.append(row + (base, relative))
    data_list.sort(key=lambda row: row[0])

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'First Value (as stored)', 'Second Value (as stored)',
                    'Marker Byte (as stored)', 'Log File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def nissan_08it_gps_logs(context):
    data_list = []
    source_paths = []
    for file_found, rows in _location_logs(context):
        source_paths.append(file_found)
        first, last = min(rows), max(rows)
        data_list.append((first[0], last[0], len(rows), first[1], first[2], last[1], last[2],
                          os.path.basename(file_found),
                          context.get_relative_path(file_found)))
    data_list.sort(key=lambda row: row[0])

    data_headers = (('First Record Time', 'datetime'), ('Last Record Time', 'datetime'),
                    'Position Records', 'First Latitude', 'First Longitude',
                    'Last Latitude', 'Last Longitude', 'Log File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

_LIST_RECORD = 260
_LIST_NAME = 256


def _file_list(data):
    """(position, name, trailing number) of each used record, or None when it does not fit.

    A record is a 256-byte name field, NUL padded, and four more bytes. The file is a
    whole number of records and the used ones come first.
    """
    if not data or len(data) % _LIST_RECORD:
        return None
    rows = []
    ended = False
    for position in range(len(data) // _LIST_RECORD):
        record = data[position * _LIST_RECORD:(position + 1) * _LIST_RECORD]
        name, _, rest = record[:_LIST_NAME].partition(b'\x00')
        if not name:
            ended = True
            continue
        if ended or rest.strip(b'\x00'):
            return None
        try:
            text = name.decode('utf-8')
        except UnicodeDecodeError:
            return None
        rows.append((position + 1, text, struct.unpack('<I', record[_LIST_NAME:])[0]))
    return rows


@artifact_processor
def nissan_08it_media_file_list(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        if not os.path.basename(file_found).startswith('file.lst'):
            continue
        rows = _file_list(_read(file_found))
        relative = context.get_relative_path(file_found)
        if rows is None:
            logfunc(f'Nissan 08IT media file list: {relative} does not have the record '
                    'layout this reader knows, not read')
            continue
        if rows:
            source_paths.append(file_found)
        folder = os.path.basename(os.path.dirname(file_found))
        for position, name, number in rows:
            data_list.append((name, folder, position, number, relative))

    data_headers = ('File Name', 'List Folder', 'Position In File',
                    'Trailing Number (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

_TRACK_PATH = re.compile(rb'/ALBUM/(\d{14})/\d\d\.[A-Z0-9]{3}\x00')
_TRACK_TITLE = 32
_TRACK_DATE = 0x126
_TRACK_NUMBER = 0x12e
_TRACK_STAMP = 0x142


def _calendar(year, month, day):
    if year == month == day == 0:
        return ''
    if 1 <= month <= 12 and 1 <= day <= 31:
        return f'{year:04d}-{month:02d}-{day:02d}'
    return None


def _library_tracks(data):
    """(rows, count the header states) for a music library file.

    A track record starts with the path of its audio file under /ALBUM/<fourteen
    digits>/. Records are not contiguous, so each is located by that path and its other
    fields are read at fixed distances from it. The 32-bit number at offset 12 of the
    file, big-endian, is the count the result is checked against.
    """
    rows = []
    for match in _TRACK_PATH.finditer(data):
        start = match.start()
        if start + _TRACK_STAMP + 7 > len(data):
            continue
        year, month, day, hour, minute, second = struct.unpack(
            '>H5B', data[start + _TRACK_STAMP:start + _TRACK_STAMP + 7])
        stamp = _calendar(year, month, day)
        other = _calendar(*struct.unpack('>HBB', data[start + _TRACK_DATE:start + _TRACK_DATE + 4]))
        if not stamp or other is None or hour > 23 or minute > 59 or second > 59:
            continue
        title = data[start + _TRACK_TITLE:start + _TRACK_DATE].split(b'\x00', 1)[0]
        number = struct.unpack('>H', data[start + _TRACK_NUMBER:start + _TRACK_NUMBER + 2])[0]
        rows.append((f'{stamp} {hour:02d}:{minute:02d}:{second:02d}', other, number,
                     title.decode('utf-8', 'replace'),
                     match.group(0)[:-1].decode('ascii'), start))
    stated = struct.unpack('>I', data[12:16])[0] if len(data) >= 16 else None
    return rows, stated


@artifact_processor
def nissan_08it_music_library(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        if not os.path.basename(file_found).startswith('cl.dtb'):
            continue
        rows, stated = _library_tracks(_read(file_found))
        relative = context.get_relative_path(file_found)
        if len(rows) != stated:
            logfunc(f'Nissan 08IT music library: {relative} states {stated} tracks and '
                    f'{len(rows)} records were found')
        if rows:
            source_paths.append(file_found)
        for stamp, other, number, title, path, offset in rows:
            data_list.append((stamp, other, number, title, path, offset, relative))

    data_headers = ('Stored Date And Time (as stored)', 'Other Stored Date (as stored)',
                    'Number After Other Date (as stored)', 'Title', 'Audio File Path',
                    'Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)

_ALBUM_FIRST = 0x4a0
_ALBUM_RECORD = 920
_ALBUM_COUNT = 0x100
_ALBUM_STAMP = 0x298


def _library_albums(data):
    """(position, name, stored count, date and time) per album record, or None.

    The 32-bit number at the start of the file, big-endian, is the number of album
    records. They are 920 bytes each from offset 0x4a0: a NUL-terminated name, a count at
    0x100 and seven bytes of date and time at 0x298. The file is given up when any of
    those records does not hold a valid date and time.
    """
    if len(data) < 4:
        return None
    albums = struct.unpack('>I', data[:4])[0]
    if not 0 < albums <= 1000 or _ALBUM_FIRST + albums * _ALBUM_RECORD > len(data):
        return None
    rows = []
    for position in range(albums):
        start = _ALBUM_FIRST + position * _ALBUM_RECORD
        year, month, day, hour, minute, second = struct.unpack(
            '>H5B', data[start + _ALBUM_STAMP:start + _ALBUM_STAMP + 7])
        stamp = _calendar(year, month, day)
        if not stamp or hour > 23 or minute > 59 or second > 59:
            return None
        name = data[start:start + _ALBUM_COUNT].split(b'\x00', 1)[0]
        count = struct.unpack('>I', data[start + _ALBUM_COUNT:start + _ALBUM_COUNT + 4])[0]
        rows.append((f'{stamp} {hour:02d}:{minute:02d}:{second:02d}',
                     name.decode('utf-8', 'replace'), count, position + 1))
    return rows


@artifact_processor
def nissan_08it_music_library_albums(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        if not os.path.basename(file_found).startswith('cl.dtb'):
            continue
        rows = _library_albums(_read(file_found))
        relative = context.get_relative_path(file_found)
        if rows is None:
            logfunc(f'Nissan 08IT music library: {relative} does not have the album '
                    'record layout this reader knows, albums not read')
            continue
        source_paths.append(file_found)
        for row in rows:
            data_list.append(row + (relative,))

    data_headers = ('Stored Date And Time (as stored)', 'Album Name',
                    'Stored Count (as stored)', 'Position In File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


_DISC_MARK = b'\x00\x00\x00\x03\x00\x00\x00'
_DISC_COUNT = 0x1c
_DISC_TEXT = 0x1b6


def _disc_fields(data, offset, count):
    """count values stored as a 32-bit length and that many bytes; (values, end) or None."""
    values = []
    for _ in range(count):
        if offset + 4 > len(data):
            return None
        length = struct.unpack('>I', data[offset:offset + 4])[0]
        if length > 512 or offset + 4 + length > len(data):
            return None
        values.append(data[offset + 4:offset + 4 + length])
        offset += 4 + length
    return values, offset


def _disc_records(data):
    """(offset, album, artist, year, tracks) for each disc record whose framing holds.

    A record is taken only when nine header values and then six values for each track
    can be read as lengths and bytes, the track count is four bytes holding a number
    from 1 to 99, the 16-bit number at 0x1c of the record is that count plus one, and
    the names decode as UTF-8.
    """
    records = []
    for start in range(len(data) - _DISC_TEXT):
        if data[start:start + len(_DISC_MARK)] != _DISC_MARK:
            continue
        head = _disc_fields(data, start + _DISC_TEXT, 9)
        if not head or len(head[0][5]) != 4 or len(head[0][6]) != 4:
            continue
        values, offset = head
        count = struct.unpack('>I', values[6])[0]
        stored = struct.unpack('>H', data[start + _DISC_COUNT:start + _DISC_COUNT + 2])[0]
        if not 1 <= count <= 99 or stored != count + 1:
            continue
        tracks = []
        try:
            album = values[0].decode('utf-8')
            artist = values[1].decode('utf-8')
            year = values[4].decode('utf-8').strip('\x00')
            for _ in range(count):
                found = _disc_fields(data, offset, 6)
                if not found:
                    raise ValueError
                offset = found[1]
                tracks.append((found[0][0].decode('utf-8'), found[0][1].decode('utf-8')))
        except ValueError:
            continue
        records.append((start, album, artist, year, tracks))
    return records


@artifact_processor
def nissan_08it_disc_titles(context):
    data_list = []
    source_paths = []
    for file_found in _regular_files(context):
        relative = context.get_relative_path(file_found)
        records = _disc_records(_read(file_found))
        if records:
            source_paths.append(file_found)
        for start, album, artist, year, tracks in records:
            for number, (title, track_artist) in enumerate(tracks, start=1):
                data_list.append((album, artist, year, number, title, track_artist,
                                  len(tracks), start, relative))

    data_headers = ('Album', 'Album Artist', 'Year', 'Track Number', 'Track Title',
                    'Track Artist', 'Tracks In Record', 'Record Offset', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Navigation backup records
# ---------------------------------------------------------------------------

_BACKUP_MAGIC = b'NEPO'
_BACKUP_RECORD = 268
_BACKUP_MARK = bytes.fromhex('09000000000000000300000000000000')
_BACKUP_MARK_AT = 0x8c
_BACKUP_TEXT = 64
_BACKUP_DATE = 0x70
_BACKUP_GRID = 0x9c


def _backup_records(data):
    """(offset, date, text, second text, grid code, grid x, grid y) for each named record.

    A record is taken where the sixteen marker bytes stand at their place, the first text
    field holds text and the date field holds a calendar date or zeros. Returns the rows
    and how many marked records were left out.
    """
    rows = []
    skipped = 0
    position = data.find(_BACKUP_MARK)
    while position != -1:
        start = position - _BACKUP_MARK_AT
        if start >= 0 and start + _BACKUP_RECORD <= len(data):
            year, month, day = struct.unpack_from('<HBB', data, start + _BACKUP_DATE)
            date = _calendar(year, month, day) if 1990 <= year <= 2100 or year == 0 else None
            text = _wide_be(data[start:start + _BACKUP_TEXT])
            if date is not None and text.strip() and text.isprintable():
                second = _wide_be(data[start + _BACKUP_TEXT:start + _BACKUP_DATE - 16])
                code, grid_x, grid_y = struct.unpack_from('<IHH', data, start + _BACKUP_GRID)
                rows.append((start, date, text, second if second.isprintable() else '',
                             f'{code:08x}', grid_x, grid_y))
            else:
                skipped += 1
        position = data.find(_BACKUP_MARK, position + 1)
    return rows, skipped


@artifact_processor
def nissan_08it_navigation_backup_records(context):
    data_list = []
    source_paths = []
    copies = {}
    order = []
    for file_found in _regular_files(context):
        data = _read(file_found)
        if not data.startswith(_BACKUP_MAGIC):
            if data:
                logfunc(f'Nissan 08IT navigation backup: {os.path.basename(file_found)} '
                        f'does not start with NEPO, not read')
            continue
        digest = hashlib.sha256(data).digest()
        if digest in copies:
            copies[digest][1] += 1
            continue
        copies[digest] = [file_found, 1, data]
        order.append(digest)
    for digest in order:
        file_found, count, data = copies[digest]
        rows, skipped = _backup_records(data)
        logfunc(f'Nissan 08IT navigation backup: {len(rows)} named records in '
                f'{os.path.basename(file_found)}, {skipped} marked records with no text '
                f'left out')
        if rows:
            source_paths.append(file_found)
        relative = context.get_relative_path(file_found)
        for start, date, text, second, code, grid_x, grid_y in rows:
            data_list.append((date, text, second, code, grid_x, grid_y, start, count,
                              relative))

    data_headers = (('Date In Record', 'date'), 'Text', 'Second Text',
                    'Value At 0x9C (as stored)', 'Value At 0xA0 (as stored)',
                    'Value At 0xA2 (as stored)',
                    'Record Offset', 'Identical Files', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
