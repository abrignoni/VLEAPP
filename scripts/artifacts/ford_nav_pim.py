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
        "description": "Phones the navigation application recorded as paired, and the "
                       "accounts it recorded against them.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. Device type, subtype and connection order are stored as integers "
                 "the application defines and are reported as stored.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "smartphone",
    },
    "ford_nav_call_log": {
        "name": "Navigation Call Log",
        "description": "Calls the navigation application synced from a paired phone.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. The time columns are reported as stored, not converted. Nothing "
                 "available here establishes their epoch or units, and while the settings "
                 "tables in the same store hold Unix seconds, a column in one table is not "
                 "evidence about a column in another. Confirm the epoch against a "
                 "populated sample before reading these values as times. The log type "
                 "column is an integer reported as stored; the table's own CHECK "
                 "constraint limits it to 1, 2 or 3, but what each value means is not "
                 "established here, so no direction is asserted. A row is a record the "
                 "vehicle copied from a phone; it does not establish who placed or "
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
        "description": "Messages the navigation application synced from a paired phone.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. The time columns are reported as stored, not converted. Nothing "
                 "available here establishes their epoch or units, and while the settings "
                 "tables in the same store hold Unix seconds, a column in one table is not "
                 "evidence about a column in another. Confirm the epoch against a "
                 "populated sample before reading these values as times. Type and folder "
                 "are integers reported as stored; the table's own CHECK constraints limit "
                 "type to 1 or 2 and folder to 1 through 6, but what each value means is "
                 "not established here, so no direction is asserted. A row is a copy the "
                 "vehicle held; it does not establish who sent or read the message.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "message-square",
    },
    "ford_nav_contacts": {
        "name": "Navigation Contacts",
        "description": "Contacts the navigation application synced from a paired phone, "
                       "with their phone numbers, email addresses and postal addresses.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. One contact can own several numbers, emails and addresses, so a "
                 "contact appears once per combination and repeated names are not "
                 "duplication. The type columns are integers the application defines and "
                 "are reported as stored.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "user",
    },
    "ford_nav_calendar": {
        "name": "Navigation Calendar",
        "description": "Calendar entries the navigation application synced from a paired "
                       "phone.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. The table carries a timezone column of its own, so an event's "
                 "local time should be read against that rather than against any zone "
                 "assumed here. The all day column is reported as stored.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows",
        },
        "output_types": "standard",
        "artifact_icon": "calendar",
    },
    "ford_nav_trips": {
        "name": "Navigation Trips",
        "description": "Trips saved in the navigation application, with their waypoints as "
                       "stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. The time columns are reported as stored, not converted. Nothing "
                 "available here establishes their epoch or units, and while the settings "
                 "tables in the same store hold Unix seconds, a column in one table is not "
                 "evidence about a column in another. Confirm the epoch against a "
                 "populated sample before reading these values as times. Waypoints, "
                 "preferences and OEM data are stored as opaque columns and are reported "
                 "as stored without decoding, because their format is not established "
                 "here. A saved trip is a route someone entered; it is not evidence the "
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
        "description": "Destination searches recorded by the navigation application.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Every table this reads was empty on the one tested extraction, where no "
                 "phone had been paired. The query was verified by staging rows into a "
                 "scratch copy of that store and confirming it executes, joins across the "
                 "related tables and returns its declared columns, so the SQL is proven "
                 "while the artifact remains unexercised against real device data. Treat a "
                 "zero row result as unconfirmed rather than as evidence the feature was "
                 "unused. The table carries a deleted flag, reported as stored, so rows "
                 "the application marked deleted are included and labelled rather than "
                 "dropped. A search string is text someone entered; it does not establish "
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
        SELECT e.subject, e.organizer, e.location, e.timezone, e.all_day, e.body,
               cal.calendar_name, d.device_name, e.calendar_event_id
        FROM calendar_event e
        LEFT JOIN calendar cal ON cal.calendar_id = e.calendar_id
        LEFT JOIN device d ON d.device_id = e.device_id
        ORDER BY e.calendar_event_id
    ''')
    return (('Subject', 'Organizer', 'Location', 'Timezone (as stored)',
             'All Day (as stored)', 'Body', 'Calendar', 'Device', 'Event ID',
             'Source File'), rows, path)


@artifact_processor
def ford_nav_trips(context):
    rows, path = _query(context, '''
        SELECT modified_timestamp, trip_name, trip_description, starting_waypoint,
               ending_waypoint, waypoints, trip_status, data_source, profile_id,
               is_visible, pending_delete, pending_timestamp, guid
        FROM trips
        ORDER BY modified_timestamp
    ''')
    return (('Modified (as stored)', 'Trip Name', 'Description', 'Start Waypoint',
             'End Waypoint', 'Waypoints (as stored)', 'Status (as stored)',
             'Data Source (as stored)', 'Profile', 'Is Visible (as stored)',
             'Pending Delete (as stored)', 'Pending (as stored)', 'GUID',
             'Source File'), rows, path)


@artifact_processor
def ford_nav_search_history(context):
    rows, path = _query(context, '''
        SELECT search_string, isDeleted, search_history_id
        FROM search_history
        ORDER BY search_history_id
    ''')
    return (('Search String', 'Is Deleted (as stored)', 'Search ID', 'Source File'),
            rows, path)
