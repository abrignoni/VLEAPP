"""Ford SYNC 4: the storage quota database each web application keeps.

The module's screens are web applications, and each keeps a browser-engine profile in a
system_handled folder. Beside the IndexedDB and Local Storage stores that
ford_hmi_indexeddb.py and ford_hmi_localstorage.py read, the profile holds:

    <application>/system_handled/QuotaManager    SQLite, table buckets

One buckets row records how often the application's storage was used and when it was
last accessed and modified.
"""

import os
import sqlite3
from datetime import datetime, timedelta

from scripts.ilapfuncs import artifact_processor, logfunc, open_sqlite_db_readonly

__artifacts_v2__ = {
    "ford_sync4_web_app_storage": {
        "name": "Ford SYNC 4 - Web Application Storage Use",
        "description": "One row for each web application's storage bucket: the application "
                       "folder, the use count and the last accessed and last modified times "
                       "its quota database stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the buckets table of <application>/system_handled/QuotaManager, the "
                 "quota database of the browser engine each SYNC 4 web application runs in. "
                 "Tested on one Ford SYNC 4 unit read from its logical zip: seven applications "
                 "(charge, phone, radio, tire pressure, trip, a com.ford.mcs application and "
                 "the owner's guide), one row each. A tested BMW MGU logical zip has no such "
                 "file. The two times are stored as whole numbers. They are read as "
                 "microseconds since 1601-01-01; read that way the seven last accessed values "
                 "fall between 2023-11-27 and 2024-04-04, and the latest is the date of the "
                 "last boot in the same unit's stability monitor log, which is the check made "
                 "here. They are written out with no offset applied; whether the stored values "
                 "are UTC was not checked here. The stored numbers are shown beside them. Use "
                 "Count is the number the row stores, from 3 to 5,657 on the tested unit; what "
                 "the engine counts as a use is not established here. Application Folder is "
                 "the folder the profile sits in. A row records that the application's storage "
                 "was last touched at that time. It does not establish what was done in the "
                 "application or by whom.",
        "paths": ('*/system_handled/QuotaManager',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 7 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, logical zip | 0 rows, no QuotaManager file "
                                         "in the zip",
        },
        "output_types": "standard",
        "artifact_icon": "globe",
    },
}

_EPOCH = datetime(1601, 1, 1)
_SKIPPED_FOLDERS = ('system_handled', 'user-data')


def _engine_time(value):
    """A stored time as text; '' when it is zero, not a number or out of range."""
    if not isinstance(value, int) or value <= 0:
        return ''
    try:
        return (_EPOCH + timedelta(microseconds=value)).strftime('%Y-%m-%d %H:%M:%S')
    except OverflowError:
        return ''


def _application(relative):
    parts = [part for part in relative.replace('\\', '/').split('/')[:-1]
             if part not in _SKIPPED_FOLDERS]
    return parts[-1] if parts else ''


@artifact_processor
def ford_sync4_web_app_storage(context):
    data_list = []
    source_paths = []
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found) or os.path.basename(file_found) != 'QuotaManager':
            continue
        relative = context.get_relative_path(file_found)
        db = open_sqlite_db_readonly(file_found)
        if db is None:
            continue
        try:
            rows = db.execute('SELECT storage_key, name, use_count, last_accessed, '
                              'last_modified FROM buckets ORDER BY id').fetchall()
        except sqlite3.Error as ex:
            logfunc(f'Ford SYNC 4 web application storage: could not read buckets in '
                    f'{relative}: {ex}')
            continue
        finally:
            db.close()
        if rows:
            source_paths.append(file_found)
        for storage_key, name, use_count, accessed, modified in rows:
            data_list.append((_engine_time(accessed), _engine_time(modified),
                              _application(relative), use_count, storage_key, name,
                              accessed, modified, relative))

    data_headers = (('Last Accessed', 'datetime'), ('Last Modified', 'datetime'),
                    'Application Folder', 'Use Count', 'Storage Key', 'Bucket Name',
                    'Last Accessed (as stored)', 'Last Modified (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
