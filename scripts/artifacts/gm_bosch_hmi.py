"""GM infotainment head unit built by Bosch (HMI module, generations 2.0 and 2.5).

One module covers the unit rather than one vehicle brand, because the same unit is
fitted across GM brands: the samples behind it are Chevrolet and GMC trucks and a
Chevrolet coupe. The stores are SQLite databases and small text files on the unit's
writable partition. Generation 2.0 keeps the Bluetooth stores under telematics/ and
generation 2.5 under connectivity/connectivity_mw/, with the same table layouts, so
every artifact here names both locations.

The unit clears its call history tables, and on every sample the calls were found
only on the database's freelist. _freelist_rows reads those pages as the table leaf
pages they still are. It follows the freelist the database header points to and
decodes each cell with the SQLite record format. It does not scan for byte patterns.
"""

import os
import re
import sqlite3
import struct
from datetime import datetime

from scripts.ilapfuncs import (artifact_processor, check_in_embedded_media, device_info,
                               logfunc, open_sqlite_db_readonly)

__artifacts_v2__ = {
    "gm_bosch_hmi_bt_devices": {
        "name": "GM Bosch HMI - Bluetooth Devices",
        "description": "Rows of the head unit's Bluetooth device table, with the device name "
                       "and address, the paired and last connected clock readings, and the "
                       "voice mail number and USB-style vendor and product identifiers the row "
                       "carries.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From table_devices in bluetooth.db (generation 2.5) or fc_bluetooth.db "
                 "(generation 2.0). Tested on six units: a 2014 Chevrolet Silverado 1500 "
                 "(generation 2.0) and, on generation 2.5, a 2016 Chevrolet Silverado 1500, a "
                 "2016 GMC Sierra 1500 and three Chevrolet Camaro (2017 and 2018). The store "
                 "records no time zone, so each time is the unit's clock reading, written out "
                 "as if it were UTC with no offset applied. Readings in 1970, 2013 and 2029 "
                 "occur among the tested units beside readings years apart from them, so a "
                 "reading on its own does not establish when an event happened. The address is "
                 "stored as twelve hex digits and shown with colons. Voice Mail Number is the "
                 "column col_szVoiceMailNumber as stored; what the unit puts there is not "
                 "established here. Vendor ID, Product ID and Version are absent from the "
                 "generation 2.0 table and shown empty for it. The link keys the table holds "
                 "are not surfaced. The status and capability integers are not surfaced "
                 "because nothing available here documents their values. A row records that "
                 "the unit held a pairing record for the device. It does not establish who "
                 "carried the device. The unit's own Bluetooth address, from "
                 "Vehicle_Info_Table, is in the Unit Information artifact.",
        "paths": (
            '*/connectivity/connectivity_mw/bluetooth.db*',
            '*/telematics/bluetoothdb/fc_bluetooth.db*',
        ),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 3 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 1 "
                             "row",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 6 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 2 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 3 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 10 rows",
        },
        "output_types": "standard",
        "artifact_icon": "bluetooth",
    },
    "gm_bosch_hmi_contacts": {
        "name": "GM Bosch HMI - Phonebook Contacts",
        "description": "Contacts in the head unit's per-device phonebook tables, with names, "
                       "phone numbers, emails, postal addresses and the contact photo when the "
                       "row holds one. Includes rows read from the database's freelist pages, "
                       "marked in Record Source.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From PhoneBook_DH2 to PhoneBook_DH11 and PhoneBook_VPB in phonebook.db. "
                 "Tested on six units: a 2014 Chevrolet Silverado 1500 (generation 2.0) and, "
                 "on generation 2.5, a 2016 Chevrolet Silverado 1500, a 2016 GMC Sierra 1500 "
                 "and three Chevrolet Camaro (2017 and 2018). Device Handle is the TableIndex "
                 "that PhoneBook_Master records for the contact, and Bluetooth Address is the "
                 "address PhoneBook_FeatureSUpport records for that handle in the same "
                 "database. On every tested unit the number in the table name equalled that "
                 "handle. PhoneBook_VPB rows have TableIndex 1, for which the database records "
                 "no address; it was populated on one unit, with three rows of address text. "
                 "Rows marked 'freelist page' were read from table leaf pages the database has "
                 "released, and are kept when they have the column count of these tables. "
                 "Which table such a row came from is not recorded. A freelist row identical "
                 "to a current row is not repeated. A freelist row gets a Device Handle only "
                 "when its Contact Handle is still in PhoneBook_Master. Freelist rows that "
                 "continue onto overflow pages are skipped and counted in the log, and pages "
                 "the database has already reused are not read. Geocodes are the stored "
                 "integers scaled by 360/2^32 into degrees. That scale is derived from the "
                 "data: the navigation artifact for the same unit states the check, and one "
                 "geocoded contact holds the same two integers as the recent destination with "
                 "the same address text. A photo is shown only when the stored bytes start "
                 "with a JPEG or PNG signature. A phonebook row records that the unit held the "
                 "contact. It does not establish that any number was dialled. The PoiName and "
                 "Notes columns were empty on every tested row and are not surfaced.",
        "paths": (
            '*/connectivity/connectivity_mw/phonebook.db*',
            '*/telematics/addressdb/phonebook.db*',
        ),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 1397 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 459 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 963 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 1384 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 769 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 4141 rows",
        },
        "output_types": "standard",
        "artifact_icon": "book-open",
    },
    "gm_bosch_hmi_call_history": {
        "name": "GM Bosch HMI - Call History",
        "description": "Call history rows from the head unit's phonebook database, with the "
                       "call clock reading, the call type, and the name and number the row "
                       "carried. On the six tested units the rows came from the database's "
                       "freelist pages and the call tables themselves were empty.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From CallHist_DEVICE0 and CallHist_DEVICE1 in phonebook.db, and from table "
                 "leaf pages on the database's freelist whose records have the eight-column "
                 "shape of those tables with an eight-digit date and a six-digit time. Tested "
                 "on six units: a 2014 Chevrolet Silverado 1500 (generation 2.0) and, on "
                 "generation 2.5, a 2016 Chevrolet Silverado 1500, a 2016 GMC Sierra 1500 and "
                 "three Chevrolet Camaro (2017 and 2018). Both tables were empty on all six, "
                 "and the freelist gave 50, 135, 50, 63, 121 and 50 distinct rows. Which of "
                 "the two tables a freelist row came from is not recorded, so Record Source "
                 "names the page. Call Type is decoded as 1 Missed, 2 Incoming, 3 Outgoing, "
                 "with the stored value alongside. That mapping was derived by comparison: on "
                 "five units an independent parse of the same database labelled the same "
                 "calls, and all 334 calls common to both agreed with no conflict. Any other "
                 "value is shown as stored. That independent parse held 13 calls on two units "
                 "that this artifact does not reach; it reads whole freelist leaf pages only, "
                 "and does not carve free space inside pages or pages already reused. The "
                 "store records no time zone, so each time is the unit's clock reading, "
                 "written out as if it were UTC with no offset applied. Readings in 1970, 2013 "
                 "and 2029 occur among the tested units beside readings years apart from them, "
                 "so a reading on its own does not establish when an event happened. Device "
                 "Handle and Bluetooth Address are filled only when the row's Contact Handle "
                 "is still in PhoneBook_Master; the handle and address are then the ones "
                 "recorded for that contact. Identical freelist rows are reported once. A row "
                 "records that the unit held this call entry. How it came to be written is not "
                 "established here, and it does not establish who used the handset.",
        "paths": (
            '*/connectivity/connectivity_mw/phonebook.db*',
            '*/telematics/addressdb/phonebook.db*',
        ),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 50 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 135 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 50 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 63 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 121 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 50 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "gm_bosch_hmi_media_devices": {
        "name": "GM Bosch HMI - Media Devices",
        "description": "Rows of the media player's device table: USB, Bluetooth audio and "
                       "other media sources the unit recorded, with the last connected clock "
                       "reading, the device name, identifier, serial number and connection "
                       "count.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From the Devices table of media/db/MyMedia.db on generation 2.5 and the "
                 "Medium table on generation 2.0. Tested on six units: a 2014 Chevrolet "
                 "Silverado 1500 (generation 2.0) and, on generation 2.5, a 2016 Chevrolet "
                 "Silverado 1500, a 2016 GMC Sierra 1500 and three Chevrolet Camaro (2017 and "
                 "2018). The store records no time zone, so each time is the unit's clock "
                 "reading, written out as if it were UTC with no offset applied. Readings in "
                 "1970, 2013 and 2029 occur among the tested units beside readings years apart "
                 "from them, so a reading on its own does not establish when an event "
                 "happened. The 2.5 database declares virtual tables this tool cannot load; "
                 "Devices is an ordinary table and reads without them. On two units the "
                 "current MyMedia.db was malformed and gave no rows, while a recovered earlier "
                 "copy of the file in the same extraction read cleanly, so every file matching "
                 "the name is read and Source File says which one a row came from. The same "
                 "device can therefore appear once per file. Device Type, Connection Type and "
                 "DiPO Capable are shown as stored because nothing available here documents "
                 "their values. The Medium table has no serial number, firmware, mount point "
                 "or connection type, and those columns are empty for it; its Medium value is "
                 "shown under Device Type. Total and free size were 0 on every tested row but "
                 "one and are not surfaced. Identifier is the UUID column as stored; on the "
                 "tested units it held USB descriptor strings, serial-like strings, "
                 "hexadecimal strings or nothing. The track library the same database indexes "
                 "(hundreds to thousands of rows naming files on the attached media) is not "
                 "listed; it describes the media's contents, and is in MediaObjects or "
                 "MediaObject for an examiner who needs it. A row records that the unit "
                 "registered the source. It does not establish what was played.",
        "paths": ('*/media/db/MyMedia.db*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 5 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 28 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 22 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 14 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 15 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 14 rows",
        },
        "output_types": "standard",
        "artifact_icon": "hard-drive",
    },
    "gm_bosch_hmi_projection_devices": {
        "name": "GM Bosch HMI - Phone Projection Device History",
        "description": "Rows of the smartphone-integration device history table, with the "
                       "device name and manufacturer stored in each, and the category, type "
                       "and support values as stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From DeviceHistory in spi/DeviceHistory.db, present on the five generation "
                 "2.5 units and absent on the generation 2.0 unit. The table carries no time "
                 "column. Access Index is u32AccessIndex as stored; that a higher value means "
                 "a more recent use is not established here. The category, type and support "
                 "columns are shown as stored because nothing available here documents their "
                 "values; bAAPSupport and bMLSupport are the unit's own column names. Those "
                 "two and enDeviceType were added by later software and are shown empty on "
                 "units whose table lacks them. The model name and Bluetooth address columns "
                 "held an empty string on every tested row, and the connection type and DAP "
                 "support columns held one value per unit; those four and the selected-device "
                 "column are not surfaced. A row records that the unit listed the device for "
                 "phone projection. It does not establish that a projection session took "
                 "place.",
        "paths": ('*/spi/DeviceHistory.db*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 0 rows, "
                             "spi/DeviceHistory.db not present",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 7 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 9 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 1 row",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 9 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 13 rows",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "gm_bosch_hmi_nav_recent_destinations": {
        "name": "GM Bosch HMI - Navigation Recent Destinations",
        "description": "Rows of the navigation unit's recent destination memory, with the "
                       "access clock reading as Timestamp, the destination name and address "
                       "parts, and the stored coordinates.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From recent_dest_memory in navstorage/navstore.db. Present on the one tested "
                 "unit with embedded navigation (2014 Chevrolet Silverado 1500, generation "
                 "2.0), where it held 128 rows; the five generation 2.5 units had no "
                 "navstore.db. The store records no time zone, so each time is the unit's "
                 "clock reading, written out as if it were UTC with no offset applied. "
                 "Readings in 1970, 2013 and 2029 occur among the tested units beside readings "
                 "years apart from them, so a reading on its own does not establish when an "
                 "event happened. Latitude and Longitude are the stored integers scaled by "
                 "360/2^32 into degrees. That scale is derived from the data: 124 of the 128 "
                 "rows named a US state in their text and all 124 decoded to a point inside "
                 "that state's bounds. The table's telephone and zip code columns were empty "
                 "on every row and are not surfaced. Position is the stored list position. A "
                 "row records that the destination was in the unit's recent list with that "
                 "access time. It does not establish that the vehicle travelled there. The "
                 "tables tour_list, tour_name_list, favourites and weather_map in the same "
                 "database held no rows on the tested unit and are not read.",
        "paths": ('*/navstorage/navstore.db*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 128 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 0 "
                             "rows, navstore.db not present",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 0 rows, navstore.db not "
                             "present",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "gm_bosch_hmi_nav_address_entries": {
        "name": "GM Bosch HMI - Navigation Address Entries",
        "description": "Dated rows of the navigation unit's autocomplete table: address text "
                       "with the access clock reading and the stored entry type.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From autocomplete in navstorage/navstore.db, on the one tested unit with "
                 "embedded navigation. Only rows with an access date are reported. The table "
                 "also held 512 undated rows of type 10, at positions 1 to 512, whose text is "
                 "point-of-interest category names (the list starts 24 H, AFRICAN, AIRPORTS); "
                 "they are left out. Entry Type is AutoComplete_Type as stored; nothing "
                 "available here documents its values. AutoCompleteEnumType held 1 on all nine "
                 "dated rows and is not surfaced. The store records no time zone, so each time "
                 "is the unit's clock reading, written out as if it were UTC with no offset "
                 "applied. Readings in 1970, 2013 and 2029 occur among the tested units beside "
                 "readings years apart from them, so a reading on its own does not establish "
                 "when an event happened. A row records address text the unit kept for "
                 "completion. Who entered it is not established.",
        "paths": ('*/navstorage/navstore.db*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 9 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 0 "
                             "rows, navstore.db not present",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 0 rows, navstore.db not "
                             "present",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, navstore.db not present",
        },
        "output_types": "standard",
        "artifact_icon": "edit-3",
    },
    "gm_bosch_hmi_custom_messages": {
        "name": "GM Bosch HMI - Added Predefined Messages",
        "description": "Rows of the predefined text message table whose creation type differs "
                       "from the value the unit's stock messages carry.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From PredefMsgTable in messaging.db (generation 2.5) or fc_messaging.db "
                 "(generation 2.0). Tested on six units: a 2014 Chevrolet Silverado 1500 "
                 "(generation 2.0) and, on generation 2.5, a 2016 Chevrolet Silverado 1500, a "
                 "2016 GMC Sierra 1500 and three Chevrolet Camaro (2017 and 2018). All six "
                 "units held the same 408 rows with PredefMsgCreatType 1, twelve for each of "
                 "34 PredefMsgLanType values; those are the unit's stock replies and are not "
                 "listed. One tested unit held two further rows with creation type 2 and "
                 "message text not in the catalogue, and the other five held none. This "
                 "artifact reports rows whose creation type is not 1. That such a row was "
                 "typed on the unit is the reading the data supports, and is not documented. "
                 "Modification Value is PredefMsgModTime as stored; it held small integers, "
                 "not a time. The generation 2.0 store also has a one-row MsgSignTable holding "
                 "a signature line; whether that text is the unit's default is not established "
                 "and it is not reported. No sent or received message is stored in this "
                 "database.",
        "paths": (
            '*/connectivity/connectivity_mw/messaging.db*',
            '*/telematics/messagingdb/fc_messaging.db*',
        ),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 0 rows, every "
                             "PredefMsgTable row had creation type 1",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 2 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 0 rows, every PredefMsgTable "
                             "row had creation type 1",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, every PredefMsgTable row "
                             "had creation type 1",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 0 rows, every PredefMsgTable row "
                             "had creation type 1",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 0 rows, every PredefMsgTable row "
                             "had creation type 1",
        },
        "output_types": "standard",
        "artifact_icon": "message-square",
    },
    "gm_bosch_hmi_voice_recordings": {
        "name": "GM Bosch HMI - Voice Command Recordings",
        "description": "Audio capture files the speech interaction logger left on the unit, "
                       "with the clock reading in each file name, the file size and the audio "
                       "wrapped so it can be played.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From interactionlogger/pcm_recordings/record<date>_<time>.pcm. Tested on six "
                 "units: a 2014 Chevrolet Silverado 1500 (generation 2.0) and, on generation "
                 "2.5, a 2016 Chevrolet Silverado 1500, a 2016 GMC Sierra 1500 and three "
                 "Chevrolet Camaro (2017 and 2018). They held between 3 and 10 such files "
                 "each. The Timestamp is read from the file name. The store records no time "
                 "zone, so each time is the unit's clock reading, written out as if it were "
                 "UTC with no offset applied. Readings in 1970, 2013 and 2029 occur among the "
                 "tested units beside readings years apart from them, so a reading on its own "
                 "does not establish when an event happened. The files are headerless samples "
                 "and do not state their format. Audio is the same bytes with a WAV header "
                 "added that declares one channel, 16-bit little-endian samples at 16,000 per "
                 "second; the evidence file is not changed. That format is a reading of the "
                 "data and not documented: on every tested file with content the values run "
                 "far more smoothly as 16-bit little-endian than as big-endian and adjacent "
                 "samples are closer than alternate ones, which fits a single channel, and on "
                 "one unit an independent parse gave ten durations that equal file size "
                 "divided by 32,000. If playback sounds wrong the declared rate or channel "
                 "count is the first thing to doubt, and the original file is named in Source "
                 "File. Duration At 16 kHz is the file size divided by 32,000. A zero-byte "
                 "file is listed with no audio. Interactionlogger.txt beside the recordings is "
                 "a hexadecimal event log with no documented layout and is not parsed. A "
                 "recording establishes that the unit captured that audio. It does not "
                 "establish who was speaking.",
        "paths": ('*/interactionlogger/pcm_recordings/record*.pcm*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 10 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 10 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 10 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 3 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 10 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 10 rows",
        },
        "output_types": "standard",
        "artifact_icon": "mic",
    },
    "gm_bosch_hmi_iapps_devices": {
        "name": "GM Bosch HMI - Internet Apps Device Table",
        "description": "Rows of the internet applications database's device table: a device "
                       "address with the type, last connected value and phone number stored "
                       "beside it.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "From deviceTable in internet/database/IAdatabase.db. Tested on six units: a "
                 "2014 Chevrolet Silverado 1500 (generation 2.0) and, on generation 2.5, a "
                 "2016 Chevrolet Silverado 1500, a 2016 GMC Sierra 1500 and three Chevrolet "
                 "Camaro (2017 and 2018). Three held rows (3, 43 and 18) and three held none. "
                 "Every tested row had device type 1, an empty last connected value and no "
                 "phone number, so the Last Connected and Phone Number columns are empty on "
                 "these samples and Device Type held 1 on every row. The unit with 43 rows "
                 "held 3 paired Bluetooth devices, so this table is not the pairing list; what "
                 "causes an address to be written here is not established. The application "
                 "catalogue, tokens and diagnostic rows in the same database are not surfaced.",
        "paths": ('*/internet/database/IAdatabase.db*',),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 0 rows, deviceTable "
                             "held no rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 0 "
                             "rows, deviceTable held no rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 0 rows, deviceTable held no "
                             "rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 3 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 43 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 18 rows",
        },
        "output_types": "standard",
        "artifact_icon": "wifi",
    },
    "gm_bosch_hmi_unit_info": {
        "name": "GM Bosch HMI - Unit Information",
        "description": "Identifiers and software versions the head unit stores: the learned "
                       "VIN, the unit's Bluetooth address, software and build version strings, "
                       "the Bosch part number and the last connected network name.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "GM Bosch HMI",
        "notes": "One row per value, with the file it came from. Sources: LearnedVIN, the "
                 "version text files on the system partition, buildversion.reg, boschpn.txt, "
                 "Vehicle_Info_Table in the Bluetooth database, the System table of MyMedia.db "
                 "and the LastConnectedNetwork key of IAdatabase.db. Tested on six units: a "
                 "2014 Chevrolet Silverado 1500 (generation 2.0) and, on generation 2.5, a "
                 "2016 Chevrolet Silverado 1500, a 2016 GMC Sierra 1500 and three Chevrolet "
                 "Camaro (2017 and 2018). Not every unit carries every file: LearnedVIN was "
                 "present on the generation 2.0 unit only. Values are reported as stored. The "
                 "learned VIN is what the unit recorded, and a unit moved between vehicles "
                 "could carry an earlier one.",
        "paths": (
            '*/ffs/LearnedVIN*',
            '*/bosch_gm_version.txt*',
            '*/gm_version.txt*',
            '*/rfs_version.txt*',
            '*/lmm_pers/buildversion.reg*',
            '*/boschpn.txt*',
            '*/connectivity/connectivity_mw/bluetooth.db*',
            '*/telematics/bluetoothdb/fc_bluetooth.db*',
            '*/media/db/MyMedia.db*',
            '*/internet/database/IAdatabase.db*',
        ),
        "sample_data": {
            "xtrmp_item021": "2014 Chevrolet Silverado 1500, HMI 2.0 | 4 rows",
            "xtrmp_item022": "2016 Chevrolet Silverado 1500, HMI 2.5, extracted file set | 5 "
                             "rows",
            "xtrmp_item023": "2016 GMC Sierra 1500 SLE, HMI 2.5 | 7 rows",
            "xtrmp_item120": "2018 Chevy Camaro SS, HMI 2.5 | 12 rows",
            "xtrmp_item122": "2017 Chevy Camaro SS, HMI 2.5 | 11 rows",
            "xtrmp_item123": "2018 Chevy Camaro SS, HMI 2.5 | 11 rows",
        },
        "output_types": "standard",
        "artifact_icon": "info",
    },
}

# Derived by comparison, not documented: see the Call History notes.
CALL_TYPES = {1: 'Missed', 2: 'Incoming', 3: 'Outgoing'}

_SQLITE_MAGIC = b'SQLite format 3\x00'
_GEO_SCALE = 360.0 / 4294967296.0
_PCM_NAME = re.compile(r'^record(\d{8})_(\d{6})\.pcm')


def _files(context, *names):
    """Matched regular files whose base name starts with one of names, sorted."""
    found = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        if any(base.startswith(name) for name in names):
            # A journal beside a database is not the database.
            if base.endswith(('-journal', '-wal', '-shm')) or '-mj' in base:
                continue
            found.append(file_found)
    return sorted(set(found))


def _is_sqlite(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read(16) == _SQLITE_MAGIC
    except OSError:
        return False


def _open(path):
    if not _is_sqlite(path):
        return None
    try:
        return open_sqlite_db_readonly(path)
    except sqlite3.Error:
        return None


def _columns(db, table):
    try:
        return [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
    except sqlite3.Error:
        return []


def _tables(db):
    try:
        return {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.Error:
        return set()


def _select(db, table, wanted):
    """Rows of table as dicts over the wanted columns; a missing column reads as ''."""
    present = _columns(db, table)
    if not present:
        return []
    have = [col for col in wanted if col in present]
    if not have:
        return []
    try:
        rows = db.execute(
            'SELECT ' + ', '.join(f'"{col}"' for col in have) + f' FROM "{table}"').fetchall()
    except sqlite3.Error as ex:
        logfunc(f'GM Bosch HMI: could not read {table}: {ex}')
        return []
    return [{col: (row[have.index(col)] if col in have else '') for col in wanted}
            for row in rows]


def _text(value):
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return str(value)


def _mac(value):
    """Twelve stored hex digits, with or without the unit's dev_ prefix, as aa:bb:..."""
    digits = re.sub(r'[^0-9A-Fa-f]', '', _text(value).replace('dev', ''))
    if len(digits) != 12:
        return _text(value)
    return ':'.join(digits[i:i + 2] for i in range(0, 12, 2)).lower()


def _asctime(value):
    """A C asctime string ('Mon Jan  5 10:20:30 2015') as 'YYYY-MM-DD HH:MM:SS'.

    Returns '' when it does not parse.
    """
    text = ' '.join(_text(value).split())
    if not text:
        return ''
    try:
        return datetime.strptime(text, '%a %b %d %H:%M:%S %Y').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


def _iso(value):
    """'YYYY-MM-DD HH:MM:SS' or its T-separated form; '' when it is neither."""
    text = _text(value).strip().replace('T', ' ')
    try:
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


def _degrees(value):
    if not isinstance(value, int) or value == 0:
        return ''
    return round(value * _GEO_SCALE, 6)


# ---------------------------------------------------------------------------
# SQLite freelist leaf pages
# ---------------------------------------------------------------------------

def _varint(data, offset):
    value = 0
    for i in range(9):
        byte = data[offset + i]
        if i == 8:
            return (value << 8) | byte, offset + 9
        value = (value << 7) | (byte & 0x7f)
        if not byte & 0x80:
            return value, offset + i + 1
    raise ValueError('varint')


def _decode_record(payload):
    header_len, offset = _varint(payload, 0)
    if header_len > len(payload):
        raise ValueError('header')
    serials = []
    while offset < header_len:
        serial, offset = _varint(payload, offset)
        serials.append(serial)
    values = []
    pos = header_len
    for serial in serials:
        if serial == 0:
            values.append(None)
        elif 1 <= serial <= 6:
            size = (1, 2, 3, 4, 6, 8)[serial - 1]
            values.append(int.from_bytes(payload[pos:pos + size], 'big', signed=True))
            pos += size
        elif serial == 7:
            values.append(struct.unpack('>d', payload[pos:pos + 8])[0])
            pos += 8
        elif serial in (8, 9):
            values.append(serial - 8)
        elif serial >= 12 and serial % 2 == 0:
            size = (serial - 12) // 2
            values.append(payload[pos:pos + size])
            pos += size
        elif serial >= 13:
            size = (serial - 13) // 2
            values.append(payload[pos:pos + size].decode('utf-8', 'replace'))
            pos += size
        else:
            raise ValueError('serial type')
    if pos != len(payload):
        raise ValueError('record length')
    return values


def _freelist_rows(path):
    """Records on freelist pages that are still intact table leaf pages.

    Returns (rows, skipped) where rows is a list of (page number, values) and skipped
    counts cells left out because they continue onto overflow pages or do not decode.
    Follows the freelist trunk chain from the database header; a page is read only
    when its first byte is the table-leaf type.
    """
    rows = []
    skipped = 0
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except OSError:
        return rows, skipped
    if len(data) < 100 or data[:16] != _SQLITE_MAGIC:
        return rows, skipped
    page_size = struct.unpack('>H', data[16:18])[0]
    if page_size == 1:
        page_size = 65536
    if page_size < 512:
        return rows, skipped
    usable = page_size - data[20]
    page_count = len(data) // page_size
    trunk = struct.unpack('>I', data[32:36])[0]

    free_pages = []
    seen = set()
    while trunk and trunk not in seen and trunk <= page_count:
        seen.add(trunk)
        start = (trunk - 1) * page_size
        next_trunk, leaf_count = struct.unpack('>II', data[start:start + 8])
        if leaf_count > (usable - 8) // 4:
            break
        free_pages.append(trunk)
        free_pages.extend(struct.unpack(f'>{leaf_count}I',
                                        data[start + 8:start + 8 + 4 * leaf_count]))
        trunk = next_trunk

    max_local = usable - 35
    for page in free_pages:
        if not 1 < page <= page_count:
            continue
        start = (page - 1) * page_size
        if data[start] != 0x0d:
            continue
        cell_count = struct.unpack('>H', data[start + 3:start + 5])[0]
        if 8 + 2 * cell_count > page_size:
            continue
        for index in range(cell_count):
            pointer = struct.unpack('>H', data[start + 8 + 2 * index:
                                               start + 10 + 2 * index])[0]
            try:
                payload_len, offset = _varint(data, start + pointer)
                _rowid, offset = _varint(data, offset)
                if payload_len > max_local or offset + payload_len > start + page_size:
                    skipped += 1
                    continue
                rows.append((page, _decode_record(data[offset:offset + payload_len])))
            except (ValueError, IndexError, struct.error):
                skipped += 1
    return rows, skipped


# ---------------------------------------------------------------------------
# Bluetooth devices
# ---------------------------------------------------------------------------

@artifact_processor
def gm_bosch_hmi_bt_devices(context):
    data_list = []
    source_paths = []
    wanted = ('col_oPairedDateTimeStamp', 'col_oConnectedDateTimeStamp',
              'col_u8DeviceHandle', 'col_szDeviceName', 'col_szDeviceAddress',
              'col_szVoiceMailNumber', 'col_u16VendorID', 'col_u16ProductID',
              'col_u16Version')
    for file_found in _files(context, 'bluetooth.db', 'fc_bluetooth.db'):
        db = _open(file_found)
        if db is None:
            continue
        source_paths.append(file_found)
        for row in _select(db, 'table_devices', wanted):
            data_list.append((
                _asctime(row['col_oPairedDateTimeStamp']),
                _asctime(row['col_oConnectedDateTimeStamp']),
                row['col_u8DeviceHandle'], _text(row['col_szDeviceName']),
                _mac(row['col_szDeviceAddress']), _text(row['col_szVoiceMailNumber']),
                row['col_u16VendorID'], row['col_u16ProductID'], row['col_u16Version'],
                context.get_relative_path(file_found)))
        db.close()

    data_headers = (('Paired Time', 'datetime'), ('Last Connected Time', 'datetime'),
                    'Device Handle', 'Device Name', 'Bluetooth Address',
                    'Voice Mail Number', 'Vendor ID', 'Product ID', 'Version',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Phonebook contacts and call history
# ---------------------------------------------------------------------------

_NUMBER_COLUMNS = (('PrefNum', 'Preferred'), ('CellNum1', 'Cell'), ('CellNum2', 'Cell 2'),
                   ('HomeNum1', 'Home'), ('HomeNum2', 'Home 2'), ('WorkNum1', 'Work'),
                   ('WorkNum2', 'Work 2'), ('OtherNum', 'Other'))
_EMAIL_COLUMNS = ('EmailAdd1', 'EmailAdd2', 'EmailAdd3')
_ADDRESS_COLUMNS = (('HomeAdd', 'Home'), ('WorkAdd', 'Work'), ('OtherAdd', 'Other'))
_GEOCODE_COLUMNS = (('Home', 'HomeGeoCodeLatitude', 'HomeGeocodeLongitude'),
                    ('Work', 'WorkGeoCodeLatitude', 'WorkGeocodeLongitude'),
                    ('Other', 'OtherGeoCodeLatitude', 'OtherGeocodeLongitude'))


def _phonebook_links(db):
    """(contact handle -> table index, table index -> address) as the database records."""
    handles = {}
    addresses = {}
    try:
        for handle, index in db.execute(
                'SELECT ContactHandle, TableIndex FROM PhoneBook_Master'):
            handles[handle] = index
    except sqlite3.Error:
        pass
    try:
        for address, handle in db.execute(
                'SELECT Address, Handle FROM PhoneBook_FeatureSUpport'):
            addresses[handle] = _mac(address)
    except sqlite3.Error:
        pass
    return handles, addresses


def _contact_tables(db):
    names = _tables(db)
    ordered = [f'PhoneBook_DH{n}' for n in range(2, 12) if f'PhoneBook_DH{n}' in names]
    if 'PhoneBook_VPB' in names:
        ordered.append('PhoneBook_VPB')
    return ordered


def _photo(file_found, blob, name):
    if not isinstance(blob, bytes) or len(blob) < 8:
        return None
    if not (blob.startswith(b'\xff\xd8\xff') or blob.startswith(b'\x89PNG\r\n\x1a\n')):
        return None
    return check_in_embedded_media(file_found, blob, name)


def _contact_row(context, file_found, record, handles, addresses, record_source):
    def joined(pairs):
        return '; '.join(f'{label}: {_text(record.get(col)).strip()}' for col, label in pairs
                         if _text(record.get(col)).strip())

    geocodes = []
    for label, lat_col, lon_col in _GEOCODE_COLUMNS:
        lat, lon = _degrees(record.get(lat_col)), _degrees(record.get(lon_col))
        if lat != '' and lon != '':
            geocodes.append(f'{label}: {lat}, {lon}')
    contact_handle = record.get('ContactHandle')
    device_handle = handles.get(contact_handle, '')
    name = ' '.join(part for part in (_text(record.get('FirstName')).strip(),
                                      _text(record.get('LastName')).strip()) if part)
    return (
        device_handle, addresses.get(device_handle, ''),
        _text(record.get('FirstName')), _text(record.get('LastName')),
        joined(_NUMBER_COLUMNS),
        '; '.join(_text(record.get(col)).strip() for col in _EMAIL_COLUMNS
                  if _text(record.get(col)).strip()),
        joined(_ADDRESS_COLUMNS), _text(record.get('Category')),
        '; '.join(geocodes), contact_handle,
        _photo(file_found, record.get('Photo'), name or 'contact photo'),
        record_source, context.get_relative_path(file_found))


def _identity(record, columns):
    """A row's content without its photo, for telling a freelist copy from a live row."""
    return tuple(_text(record.get(col)) for col in columns if col != 'Photo')


@artifact_processor
def gm_bosch_hmi_contacts(context):
    data_list = []
    source_paths = []
    for file_found in _files(context, 'phonebook.db'):
        db = _open(file_found)
        if db is None:
            continue
        tables = _contact_tables(db)
        if not tables:
            db.close()
            continue
        source_paths.append(file_found)
        handles, addresses = _phonebook_links(db)
        columns = _columns(db, tables[0])
        live = set()
        for table in tables:
            table_columns = _columns(db, table)
            try:
                rows = db.execute(f'SELECT * FROM "{table}"').fetchall()
            except sqlite3.Error as ex:
                logfunc(f'GM Bosch HMI: could not read {table}: {ex}')
                continue
            for row in rows:
                record = dict(zip(table_columns, row))
                live.add(_identity(record, table_columns))
                data_list.append(_contact_row(context, file_found, record, handles,
                                              addresses, table))
        db.close()

        freelist, skipped = _freelist_rows(file_found)
        seen = set()
        recovered = 0
        for page, values in freelist:
            if len(values) != len(columns) or not isinstance(values[0], int):
                continue
            if not all(isinstance(v, (str, type(None))) for v in values[1:20]):
                continue
            record = dict(zip(columns, values))
            identity = _identity(record, columns)
            if identity in live or identity in seen:
                continue
            seen.add(identity)
            recovered += 1
            data_list.append(_contact_row(context, file_found, record, handles, addresses,
                                          f'freelist page {page}'))
        logfunc(f'GM Bosch HMI contacts: {recovered} freelist rows, {skipped} freelist '
                f'cells skipped, in {os.path.basename(file_found)}')

    data_headers = ('Device Handle', 'Bluetooth Address', 'First Name', 'Last Name',
                    'Phone Numbers', 'Emails', 'Addresses', 'Category', 'Geocodes',
                    'Contact Handle', ('Photo', 'media'),
                    'Record Source', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _call_time(date_text, time_text):
    date_text, time_text = _text(date_text).strip(), _text(time_text).strip()
    if not (re.fullmatch(r'\d{8}', date_text) and re.fullmatch(r'\d{6}', time_text)):
        return ''
    try:
        return datetime.strptime(date_text + time_text,
                                 '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return ''


def _is_call_record(values):
    if len(values) != 8:
        return False
    if not isinstance(values[0], int) or not isinstance(values[1], int):
        return False
    if not all(isinstance(v, str) for v in values[2:]):
        return False
    return bool(re.fullmatch(r'\d{8}', values[6]) and re.fullmatch(r'\d{6}', values[7]))


@artifact_processor
def gm_bosch_hmi_call_history(context):
    data_list = []
    source_paths = []

    def add(file_found, values, handles, addresses, record_source):
        contact_handle, call_type = values[0], values[1]
        device_handle = handles.get(contact_handle, '')
        data_list.append((
            _call_time(values[6], values[7]),
            CALL_TYPES.get(call_type, ''), call_type,
            _text(values[2]), _text(values[3]), _text(values[4]), _text(values[5]),
            contact_handle, device_handle, addresses.get(device_handle, ''),
            record_source, context.get_relative_path(file_found)))

    for file_found in _files(context, 'phonebook.db'):
        db = _open(file_found)
        if db is None:
            continue
        names = _tables(db)
        if not any(name.startswith('CallHist_DEVICE') for name in names):
            db.close()
            continue
        source_paths.append(file_found)
        handles, addresses = _phonebook_links(db)
        live = set()
        for table in sorted(name for name in names if name.startswith('CallHist_DEVICE')):
            try:
                rows = db.execute(
                    'SELECT ContactHandle, CallType, FirstName, LastName, PhoneNumber, '
                    f'NumberType, CallDate, CallTime FROM "{table}"').fetchall()
            except sqlite3.Error as ex:
                logfunc(f'GM Bosch HMI: could not read {table}: {ex}')
                continue
            for row in rows:
                live.add(tuple(row))
                add(file_found, list(row), handles, addresses, table)
        db.close()

        freelist, skipped = _freelist_rows(file_found)
        seen = set()
        for page, values in freelist:
            if not _is_call_record(values):
                continue
            key = tuple(values)
            if key in live or key in seen:
                continue
            seen.add(key)
            add(file_found, values, handles, addresses, f'freelist page {page}')
        logfunc(f'GM Bosch HMI call history: {len(seen)} freelist rows, {skipped} freelist '
                f'cells skipped, in {os.path.basename(file_found)}')

    data_headers = (('Call Time', 'datetime'), 'Call Type', 'Call Type (as stored)',
                    'First Name', 'Last Name', 'Phone Number', 'Number Type (as stored)',
                    'Contact Handle', 'Device Handle', 'Bluetooth Address',
                    'Record Source', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Media and projection devices
# ---------------------------------------------------------------------------

@artifact_processor
def gm_bosch_hmi_media_devices(context):
    data_list = []
    source_paths = []
    devices = ('LastConnected', 'FriendlyName', 'UUID', 'SerialNumber', 'FirmwareVersion',
               'MountPoint', 'ConnectionCount', 'DeviceType', 'ConnectionType',
               'NumberOfFiles', 'DiPOCapable', 'ID')
    medium = ('LastConnected', 'DeviceName', 'MediumUUID', 'ConnectionCount', 'Medium',
              'TotalFiles', 'ID')
    for file_found in _files(context, 'MyMedia.db'):
        db = _open(file_found)
        if db is None:
            continue
        names = _tables(db)
        rows = []
        if 'Devices' in names:
            for row in _select(db, 'Devices', devices):
                rows.append((
                    _iso(row['LastConnected']), _text(row['FriendlyName']),
                    _text(row['UUID']), _text(row['SerialNumber']),
                    _text(row['FirmwareVersion']), _text(row['MountPoint']),
                    row['ConnectionCount'], row['DeviceType'], row['ConnectionType'],
                    row['NumberOfFiles'], row['DiPOCapable'], row['ID']))
        elif 'Medium' in names:
            for row in _select(db, 'Medium', medium):
                rows.append((
                    _iso(row['LastConnected']), _text(row['DeviceName']),
                    _text(row['MediumUUID']), '', '', '', row['ConnectionCount'],
                    row['Medium'], '', row['TotalFiles'], '', row['ID']))
        db.close()
        if 'Devices' in names or 'Medium' in names:
            source_paths.append(file_found)
        for row in rows:
            data_list.append(row + (context.get_relative_path(file_found),))

    data_headers = (('Last Connected Time', 'datetime'), 'Device Name', 'Identifier',
                    'Serial Number', 'Firmware Version', 'Mount Point', 'Connection Count',
                    'Device Type (as stored)', 'Connection Type (as stored)',
                    'Number Of Files', 'DiPO Capable (as stored)', 'Row ID',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_bosch_hmi_projection_devices(context):
    data_list = []
    source_paths = []
    wanted = ('szDeviceName', 'szDeviceMaunufacturerName', 'U32DeviceHandle',
              'u32AccessIndex', 'enDeviceCategory', 'enDeviceType', 'bAAPSupport',
              'bMLSupport', 'bDeviceUsageEnabled', 'bIsUserDeselected')
    for file_found in _files(context, 'DeviceHistory.db'):
        db = _open(file_found)
        if db is None:
            continue
        if 'DeviceHistory' not in _tables(db):
            db.close()
            continue
        source_paths.append(file_found)
        for row in _select(db, 'DeviceHistory', wanted):
            data_list.append(tuple(
                _text(row[col]) if col.startswith('sz') else row[col]
                for col in wanted) + (context.get_relative_path(file_found),))
        db.close()

    data_headers = ('Device Name', 'Manufacturer Name', 'Device Handle', 'Access Index',
                    'Device Category (as stored)', 'Device Type (as stored)',
                    'AAP Support (as stored)', 'ML Support (as stored)',
                    'Device Usage Enabled (as stored)', 'User Deselected (as stored)',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@artifact_processor
def gm_bosch_hmi_nav_recent_destinations(context):
    data_list = []
    source_paths = []
    wanted = ('access_date', 'short_name', 'house_no', 'street', 'town', 'country',
              'poiname', 'PoiCategoryName', 'Latitude', 'Longitude', 'position',
              'unique_id')
    for file_found in _files(context, 'navstore.db'):
        db = _open(file_found)
        if db is None:
            continue
        if 'recent_dest_memory' not in _tables(db):
            db.close()
            continue
        source_paths.append(file_found)
        for row in _select(db, 'recent_dest_memory', wanted):
            data_list.append((
                _iso(row['access_date']), _text(row['short_name']),
                _text(row['house_no']), _text(row['street']), _text(row['town']),
                _text(row['country']), _text(row['poiname']),
                ' '.join(_text(row['PoiCategoryName']).split()),
                _degrees(row['Latitude']),
                _degrees(row['Longitude']), row['position'], row['unique_id'],
                context.get_relative_path(file_found)))
        db.close()

    data_headers = (('Timestamp', 'datetime'), 'Name', 'House Number', 'Street', 'Town',
                    'Country', 'POI Name', 'POI Category Text', 'Latitude', 'Longitude',
                    'Position', 'Record ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def gm_bosch_hmi_nav_address_entries(context):
    data_list = []
    source_paths = []
    wanted = ('access_date', 'short_name', 'AutoComplete_Type')
    for file_found in _files(context, 'navstore.db'):
        db = _open(file_found)
        if db is None:
            continue
        if 'autocomplete' not in _tables(db):
            db.close()
            continue
        source_paths.append(file_found)
        for row in _select(db, 'autocomplete', wanted):
            stamp = _iso(row['access_date'])
            if not stamp:
                continue
            data_list.append((stamp, _text(row['short_name']), row['AutoComplete_Type'],
                              context.get_relative_path(file_found)))
        db.close()

    data_headers = (('Access Time', 'datetime'), 'Address Text', 'Entry Type (as stored)',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Messages, recordings, internet apps
# ---------------------------------------------------------------------------

@artifact_processor
def gm_bosch_hmi_custom_messages(context):
    data_list = []
    source_paths = []
    wanted = ('PredefMsg', 'PredefMsgCreatType', 'PredefMsgType', 'PredefMsgLanType',
              'PredefMsgModTime', 'PID')
    for file_found in _files(context, 'messaging.db', 'fc_messaging.db'):
        db = _open(file_found)
        if db is None:
            continue
        names = _tables(db)
        if 'PredefMsgTable' not in names:
            db.close()
            continue
        source_paths.append(file_found)
        for row in _select(db, 'PredefMsgTable', wanted):
            if row['PredefMsgCreatType'] == 1:
                continue
            data_list.append((
                _text(row['PredefMsg']), row['PredefMsgCreatType'],
                row['PredefMsgType'], row['PredefMsgLanType'], row['PredefMsgModTime'],
                row['PID'], context.get_relative_path(file_found)))
        db.close()

    data_headers = ('Message Text', 'Creation Type (as stored)',
                    'Message Type (as stored)', 'Language Type (as stored)',
                    'Modification Value (as stored)', 'Row ID', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _wav(samples):
    """Headerless samples wrapped as a WAV file: one channel, 16 kHz, 16-bit little-endian.

    Only a header is added; the sample bytes are passed through unchanged.
    """
    rate, width = 16000, 2
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(samples), b'WAVE', b'fmt ',
                         16, 1, 1, rate, rate * width, width, 8 * width, b'data',
                         len(samples))
    return header + samples


@artifact_processor
def gm_bosch_hmi_voice_recordings(context):
    data_list = []
    source_paths = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        match = _PCM_NAME.match(os.path.basename(file_found))
        if not match:
            continue
        try:
            with open(file_found, 'rb') as handle:
                samples = handle.read()
        except OSError:
            continue
        source_paths.append(file_found)
        base = os.path.basename(file_found)
        audio = None
        if len(samples) >= 2:
            audio = check_in_embedded_media(file_found, _wav(samples[:len(samples) & ~1]),
                                            base + '.wav')
        data_list.append((_call_time(match.group(1), match.group(2)), audio, base,
                          len(samples), round(len(samples) / 32000.0, 1),
                          context.get_relative_path(file_found)))
    data_list.sort(key=lambda row: (row[5], row[0]))

    data_headers = (('Timestamp', 'datetime'), ('Audio', 'media'), 'File Name',
                    'File Size (bytes)', 'Duration At 16 kHz (seconds)', 'Source File')
    return data_headers, data_list, '\n'.join(sorted(source_paths))


@artifact_processor
def gm_bosch_hmi_iapps_devices(context):
    data_list = []
    source_paths = []
    wanted = ('sLastConnected', 'sDeviceAddress', 'iDevType', 'sPhoneNumber')
    for file_found in _files(context, 'IAdatabase.db'):
        db = _open(file_found)
        if db is None:
            continue
        if 'deviceTable' not in _tables(db):
            db.close()
            continue
        source_paths.append(file_found)
        for row in _select(db, 'deviceTable', wanted):
            data_list.append((_text(row['sLastConnected']), _mac(row['sDeviceAddress']),
                              row['iDevType'], _text(row['sPhoneNumber']),
                              context.get_relative_path(file_found)))
        db.close()

    data_headers = ('Last Connected (as stored)', 'Device Address',
                    'Device Type (as stored)', 'Phone Number', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


# ---------------------------------------------------------------------------
# Unit information
# ---------------------------------------------------------------------------

_REG_VALUE = re.compile(r'^"([^"]+)"="(.*)"\s*$')
_REG_KEYS = ('BUILDVERSION_LABEL', 'BUILDVERSION_TIMESTAMP', 'BUILDVERSION_CUSTVERSTRING',
             'PRODUCT_PN_UPDATED', 'SUPPLIER_ECU_SOFTWARE_VERSION_NUMBER')
_TEXT_FILES = {'LearnedVIN': 'Learned VIN', 'bosch_gm_version.txt': 'Software Version',
               'gm_version.txt': 'Software Version', 'rfs_version.txt': 'Root Filesystem Version',
               'boschpn.txt': 'Bosch Part Number'}


def _read_text(path, limit=65536):
    try:
        with open(path, 'rb') as handle:
            return handle.read(limit).decode('utf-8', 'replace')
    except OSError:
        return ''


def _db_value(db, query):
    try:
        row = db.execute(query).fetchone()
    except sqlite3.Error:
        return ''
    return '' if row is None else row[0]


@artifact_processor
def gm_bosch_hmi_unit_info(context):
    data_list = []
    source_paths = []

    def add(label, value, file_found):
        value = _text(value).strip().strip('\x00')
        if not value:
            return
        data_list.append((label, value, context.get_relative_path(file_found)))
        if file_found not in source_paths:
            source_paths.append(file_found)
        device_info('GM Bosch HMI', label, value, context.get_relative_path(file_found))

    for file_found in sorted({str(f) for f in context.get_files_found()}):
        if os.path.isdir(file_found):
            continue
        base = os.path.basename(file_found)
        label = next((text for name, text in _TEXT_FILES.items() if base.startswith(name)),
                     None)
        if label is not None:
            for line in _read_text(file_found, 4096).splitlines():
                add(label, line, file_found)
        elif base.startswith('buildversion.reg'):
            for line in _read_text(file_found).splitlines():
                match = _REG_VALUE.match(line.strip())
                if match and match.group(1) in _REG_KEYS:
                    add(match.group(1), match.group(2), file_found)
        elif base.startswith(('bluetooth.db', 'fc_bluetooth.db', 'MyMedia.db',
                              'IAdatabase.db')):
            if base.endswith(('-journal', '-wal', '-shm')) or '-mj' in base:
                continue
            db = _open(file_found)
            if db is None:
                continue
            names = _tables(db)
            if 'Vehicle_Info_Table' in names:
                value = _db_value(db, 'SELECT Vehicle_BT_Address FROM Vehicle_Info_Table')
                if value:
                    add('Unit Bluetooth Address', _mac(value), file_found)
            if 'System' in names and 'BTMacAddress' in _columns(db, 'System'):
                value = _db_value(db, 'SELECT BTMacAddress FROM System')
                if value:
                    add('Media Player Bluetooth Address (as stored)', value, file_found)
            if 'GENERIC_TABLE' in names:
                value = _db_value(db, "SELECT value FROM GENERIC_TABLE "
                                      "WHERE key = 'LastConnectedNetwork'")
                if value:
                    add('Last Connected Network', value, file_found)
            db.close()

    data_headers = ('Property', 'Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
