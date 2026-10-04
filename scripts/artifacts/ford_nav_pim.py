"""Personal information the built-in navigation application syncs from a paired phone.

Every artifact here was written from the store's schema. All of the tables were
empty on the one extraction available, so none is exercised against real device
data. Each query was verified against a scratch copy with rows staged into it, so
the SQL is proven even though the artifact is not. That boundary is stated in
every artifact's notes rather than left to a reader.
"""

__artifacts_v2__ = {
    "ford_nav_paired_devices": {
        "name": "Navigation Paired Devices",
        "description": "Rows of the device table in the navigation application's "
                       "data_manager.sqlite, with the account rows linked to each. "
                       "Unexercised: the tables were empty on the one tested "
                       "extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. Device type, subtype and connection order are reported as "
                 "stored. The schema declares device_type and device_subtype as TEXT; what "
                 "their values mean is not established here.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "ford_nav_call_log": {
        "name": "Navigation Call Log",
        "description": "Rows of the call_log table in the navigation application's "
                       "data_manager.sqlite, with the contact and device rows they link to. "
                       "Unexercised: the table was empty on the one tested extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a scratch copy of that store and "
                 "confirming it executes, joins across the related tables and returns its "
                 "declared columns, so the SQL is proven while the artifact remains "
                 "unexercised against real device data. Treat a zero row result as "
                 "unconfirmed rather than as evidence the feature was unused. The time "
                 "columns are reported as stored, not converted. Nothing available here "
                 "establishes their epoch or units, and while the settings tables in the "
                 "same store are read as Unix times, a column in one table is not evidence "
                 "about a column in another. Confirm the epoch against a populated sample "
                 "before reading these values as times. The log type column is an integer "
                 "reported as stored; what each value means is not established here, so "
                 "no direction is asserted. How a row comes to be written is not "
                 "established here. A row does not establish who placed or "
                 "answered the call.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "phone",
    },
    "ford_nav_sms": {
        "name": "Navigation Messages",
        "description": "Rows of the sms table in the navigation application's data_manager.sqlite, "
                       "with the contact, conversation and device rows they link to. Unexercised: "
                       "the table was empty on the one tested extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a scratch copy of that store and "
                 "confirming it executes, joins across the related tables and returns its "
                 "declared columns, so the SQL is proven while the artifact remains "
                 "unexercised against real device data. Treat a zero row result as "
                 "unconfirmed rather than as evidence the feature was unused. The time "
                 "columns are reported as stored, not converted. Nothing available here "
                 "establishes their epoch or units, and while the settings tables in the "
                 "same store are read as Unix times, a column in one table is not evidence "
                 "about a column in another. Confirm the epoch against a populated sample "
                 "before reading these values as times. Type and folder are integers "
                 "reported as stored; what each value means is not established here, so no "
                 "direction is asserted. How a row comes to be written is not established "
                 "here. A row does not establish who sent or read the message.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "message-square",
    },
    "ford_nav_contacts": {
        "name": "Navigation Contacts",
        "description": "Rows of the contact table in the navigation application's "
                       "data_manager.sqlite (unexercised: empty on the one tested "
                       "extraction), "
                       "with their phone numbers, email addresses and postal addresses.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. One contact can own several numbers, emails and addresses, so a "
                 "contact appears once per combination and repeated names are not "
                 "duplication. The type columns (phone_number_type, email_type) are "
                 "declared TEXT in the schema and are reported as stored.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "user",
    },
    "ford_nav_calendar": {
        "name": "Navigation Calendar",
        "description": "Rows of the calendar_event table in the navigation application's "
                       "data_manager.sqlite, with the event_instance start and end times "
                       "linked to each. Unexercised: the tables were empty on the one "
                       "tested extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-04",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a scratch copy of that store and "
                 "confirming it executes, joins across the related tables and returns its "
                 "declared columns, so the SQL is proven while the artifact remains "
                 "unexercised against real device data. Treat a zero row result as "
                 "unconfirmed rather than as evidence the feature was unused. The "
                 "calendar_event table has no time column. Start and end times come from "
                 "the event_instance table, which the schema links to calendar_event "
                 "through a foreign key on calendar_event_id, and are reported as stored, "
                 "not converted. Nothing available here establishes their epoch or units. "
                 "An event with several event_instance rows appears once per instance, so "
                 "a repeated Event ID is not duplication, and an event with no "
                 "event_instance row appears once with blank times. The table's timezone "
                 "column is reported as stored. The all day column is reported as stored.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "calendar",
    },
    "ford_nav_trips": {
        "name": "Navigation Trips",
        "description": "Rows of the trips table in the navigation application's "
                       "data_manager.sqlite, with their waypoints as stored. Unexercised: "
                       "the table was empty on the one tested extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-04",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a scratch copy of that store and "
                 "confirming it executes and returns its declared columns, so the SQL is "
                 "proven while the artifact remains unexercised against real device data. "
                 "Treat a zero row result as unconfirmed rather than as evidence the "
                 "feature was unused. The time columns (modified_timestamp, "
                 "pending_timestamp) are declared TEXT in the schema and are reported as "
                 "stored, not converted. Nothing available here establishes their format, "
                 "and while the settings tables in the same store are read as Unix times, a "
                 "column in one table is not evidence about a column in another. Confirm "
                 "the format against a populated sample before reading these values as "
                 "times. The waypoint columns (starting_waypoint, ending_waypoint, "
                 "waypoints) and the global, trip_preferences and oem_data columns are "
                 "reported as stored without decoding. The table held 0 rows on "
                 "ford_syncg4 and ford_syncg4_logical, so the format of these columns was "
                 "not observed. "
                 "How a trips row comes to be written is not established here. A row is "
                 "not evidence the "
                 "route was driven.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map",
    },
    "ford_nav_search_history": {
        "name": "Navigation Search History",
        "description": "Rows of the search_history table in the navigation application's "
                       "data_manager.sqlite. Unexercised: the table was empty on the one tested "
                       "extraction.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction. The query "
                 "was verified by staging rows into a scratch copy of that store and "
                 "confirming it executes and returns its declared columns, so the SQL is "
                 "proven while the artifact remains unexercised against real device data. "
                 "Treat a zero row result as unconfirmed rather than as evidence the "
                 "feature was unused. The table carries a deleted flag, reported as "
                 "stored, so rows the application marked deleted are included and labelled "
                 "rather than dropped. A search string does not establish who entered it "
                 "or "
                 "that the vehicle travelled there.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "search",
    },
}
import sqlite3

from scripts.ilapfuncs import (artifact_processor, get_file_path,
                               open_sqlite_db_readonly)


def _query(context, sql):
    """Rows for one query against the navigation store, plus the relative path."""
    source_path = get_file_path(context.get_files_found(), "data_manager.sqlite")
    if not source_path:
        return [], ''
    relative_path = context.get_relative_path(source_path)
    db = open_sqlite_db_readonly(source_path)
    if db is None:
        return [], relative_path
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
    except sqlite3.Error:
        db.close()
        return [], relative_path
    db.close()
    return [row + (relative_path,) for row in rows], relative_path


@artifact_processor
def ford_nav_paired_devices(context):
    rows, path = _query(context, '''
        SELECT d.device_name, d.device_type, d.device_subtype, d.connection_order,
               d.profile_id, a.account_name, a.account_type, a.account_email,
               d.device_id
        FROM device d
        LEFT JOIN account a ON a.device_id = d.device_id
        ORDER BY d.connection_order, d.device_id
    ''')
    return (('Device Name', 'Device Type (as stored)', 'Device Subtype (as stored)',
             'Connection Order (as stored)', 'Profile', 'Account Name',
             'Account Type (as stored)', 'Account Email', 'Device ID',
             'Source File'), rows, path)


@artifact_processor
def ford_nav_call_log(context):
    rows, path = _query(context, '''
        SELECT c.phone_call_time, c.formatted_phone_number, c.phone_number,
               ct.formatted_name, c.log_type, c.duration, d.device_name, c.call_log_id
        FROM call_log c
        LEFT JOIN contact ct ON ct.contact_id = c.contact_id
        LEFT JOIN device d ON d.device_id = c.device_id
        ORDER BY c.phone_call_time
    ''')
    return (('Call Time (as stored)', 'Formatted Number', 'Number', 'Contact',
             'Log Type (as stored)', 'Duration (as stored)', 'Device', 'Call ID',
             'Source File'), rows, path)


@artifact_processor
def ford_nav_sms(context):
    rows, path = _query(context, '''
        SELECT s.message_time, s.phone_number, ct.formatted_name, s.body, s.type,
               s.folder, s.is_read, d.device_name, s.sms_conversation_id, s.sms_id
        FROM sms s
        LEFT JOIN contact ct ON ct.contact_id = s.contact_id
        LEFT JOIN sms_conversation sc ON sc.sms_conversation_id = s.sms_conversation_id
        LEFT JOIN device d ON d.device_id = sc.device_id
        ORDER BY s.message_time
    ''')
    return (('Message Time (as stored)', 'Number', 'Contact', 'Message',
             'Type (as stored)', 'Folder (as stored)', 'Is Read (as stored)',
             'Device', 'Conversation', 'Message ID', 'Source File'), rows, path)


@artifact_processor
def ford_nav_contacts(context):
    rows, path = _query(context, '''
        SELECT c.formatted_name, c.first_name, c.last_name, c.nickname,
               p.formatted_phone_number, p.phone_number_type, e.email, e.email_type,
               a.street_line1, a.municipality, a.administrative_area, a.postal_code,
               a.country, c.is_active, d.device_name, c.contact_id
        FROM contact c
        LEFT JOIN contact_phone_number p ON p.contact_id = c.contact_id
        LEFT JOIN contact_email e ON e.contact_id = c.contact_id
        LEFT JOIN contact_address a ON a.contact_id = c.contact_id
        LEFT JOIN device d ON d.device_id = c.device_id
        ORDER BY c.formatted_name, c.contact_id
    ''')
    return (('Name', 'First Name', 'Last Name', 'Nickname', 'Phone Number',
             'Number Type (as stored)', 'Email', 'Email Type (as stored)', 'Street',
             'Municipality', 'Area', 'Postal Code', 'Country',
             'Is Active (as stored)', 'Device', 'Contact ID', 'Source File'),
            rows, path)


@artifact_processor
def ford_nav_calendar(context):
    rows, path = _query(context, '''
        SELECT i.start_time, i.end_time, e.subject, e.organizer, e.location,
               e.timezone, e.all_day, e.body, cal.calendar_name, d.device_name,
               e.calendar_event_id
        FROM calendar_event e
        LEFT JOIN event_instance i ON i.calendar_event_id = e.calendar_event_id
        LEFT JOIN calendar cal ON cal.calendar_id = e.calendar_id
        LEFT JOIN device d ON d.device_id = e.device_id
        ORDER BY i.start_time, e.calendar_event_id
    ''')
    return (('Start Time (as stored)', 'End Time (as stored)', 'Subject', 'Organizer',
             'Location', 'Timezone (as stored)', 'All Day (as stored)', 'Body',
             'Calendar', 'Device', 'Event ID', 'Source File'), rows, path)


@artifact_processor
def ford_nav_trips(context):
    rows, path = _query(context, '''
        SELECT t.modified_timestamp, t.trip_name, t.trip_description,
               t.starting_waypoint, t.ending_waypoint, t.waypoints, t.trip_status,
               t.data_source, t.profile_id, t.is_visible, t.pending_delete,
               t.pending_timestamp, t."global", t.trip_preferences, t.oem_data, t.guid
        FROM trips t
        ORDER BY t.modified_timestamp
    ''')
    return (('Modified (as stored)', 'Trip Name', 'Description', 'Start Waypoint',
             'End Waypoint', 'Waypoints (as stored)', 'Status (as stored)',
             'Data Source (as stored)', 'Profile', 'Is Visible (as stored)',
             'Pending Delete (as stored)', 'Pending Timestamp (as stored)',
             'Global (as stored)', 'Trip Preferences (as stored)',
             'OEM Data (as stored)', 'GUID', 'Source File'), rows, path)


@artifact_processor
def ford_nav_search_history(context):
    rows, path = _query(context, '''
        SELECT search_string, isDeleted, search_history_id
        FROM search_history
        ORDER BY search_history_id
    ''')
    return (('Search String', 'Is Deleted (as stored)', 'Search ID', 'Source File'),
            rows, path)
