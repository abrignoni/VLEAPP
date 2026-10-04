__artifacts_v2__ = {
    "ford_nav_user_settings": {
        "name": "Navigation User Settings",
        "description": "Settings the built-in navigation application stored against a user "
                       "profile, each with the value as stored and the row's time_stamp.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the user_setting table in the navigation application's "
                 "data_manager.sqlite. time_stamp is read as a Unix time, with the unit chosen "
                 "from the value's magnitude. Setting names are the application's own and most "
                 "values are undocumented integers, so values are reported as stored and no "
                 "meaning is assigned to them. The timestamps are worth reading as a group rather "
                 "than individually: on the tested image most rows shared a timestamp within a "
                 "few seconds, and a smaller number carried later and well separated times. On "
                 "the tested image that shared timestamp fell 22 seconds after the reset recorded "
                 "in the unit's own reset-reason.txt, which is one observation. A row holds a "
                 "setting value and a time_stamp. Whether that time is when the value was set, "
                 "and whether a row flagged isDeleted is still in effect, are not established. A "
                 "row does not establish who changed it, which matters in a vehicle more than one "
                 "person may use. isBinary is reported as stored, and no value is decoded.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 50 rows",
        },
        "output_types": "standard",
        "artifact_icon": "settings",
    },
    "ford_nav_global_settings": {
        "name": "Navigation Global Settings",
        "description": "Settings the built-in navigation application stored without a user "
                       "profile, each with the value as stored and the row's time_stamp.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the global_setting table in the same store as the user settings, with "
                 "the same columns except that no profile is recorded. time_stamp is read as "
                 "a Unix time, with the unit chosen from the value's magnitude, and values "
                 "are reported as stored. On the tested image one of its settings held a "
                 "profile identifier.",
        "paths": ('*/com.garmin.sync.garmin-app/user-data/data_manager.sqlite*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 44 rows",
        },
        "output_types": "standard",
        "artifact_icon": "settings",
    },
}

from scripts.ilapfuncs import (artifact_processor, convert_unix_ts_to_utc,
                               get_file_path, open_sqlite_db_readonly)


def _settings_rows(context, query):
    """Rows from one of the two settings tables, plus the relative source path."""
    data_list = []
    source_path = get_file_path(context.get_files_found(), "data_manager.sqlite")
    if not source_path:
        return [], ''
    relative_path = context.get_relative_path(source_path)
    db = open_sqlite_db_readonly(source_path)
    if db is None:
        return [], relative_path
    cursor = db.cursor()
    cursor.execute(query)
    for row in cursor.fetchall():
        data_list.append((convert_unix_ts_to_utc(row[0]),) + row[1:]
                         + (relative_path,))
    db.close()
    return data_list, relative_path


@artifact_processor
def ford_nav_user_settings(context):
    data_list, relative_path = _settings_rows(context, '''
        SELECT time_stamp, setting_id, value, profile_id, isBinary, isDeleted
        FROM user_setting
        ORDER BY time_stamp, setting_id
    ''')
    data_headers = (('Written', 'datetime'), 'Setting', 'Value (as stored)',
                    'Profile', 'Is Binary (as stored)', 'Is Deleted (as stored)',
                    'Source File')
    return data_headers, data_list, relative_path


@artifact_processor
def ford_nav_global_settings(context):
    data_list, relative_path = _settings_rows(context, '''
        SELECT time_stamp, setting_id, value, isBinary, isDeleted
        FROM global_setting
        ORDER BY time_stamp, setting_id
    ''')
    data_headers = (('Written', 'datetime'), 'Setting', 'Value (as stored)',
                    'Is Binary (as stored)', 'Is Deleted (as stored)', 'Source File')
    return data_headers, data_list, relative_path
