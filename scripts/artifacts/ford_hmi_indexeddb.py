__artifacts_v2__ = {
    "ford_hmi_app_state": {
        "name": "HMI Application State",
        "description": "State the head unit's HMI applications persisted to IndexedDB, "
                       "including the valet mode record, the profile and phone as a key "
                       "record, trailer settings and software update state.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "The HMI applications are Chromium based and persist state to IndexedDB, "
                 "whose values are V8 serialized rather than plain text. It is read here "
                 "with the vendored ccl_chromium_indexeddb reader; scanning the raw files "
                 "cannot see Snappy compressed table blocks, cannot recover the key a value "
                 "belonged to, and would misread V8 values as JSON. IndexedDB records carry "
                 "no timestamp of their own, unlike the Local Storage artifact, so no time "
                 "is reported. Every version of a key is reported, so a key appears once "
                 "per write and the values can be read as a sequence. The theme store is "
                 "deliberately not included: it holds display styling. On the tested image "
                 "the valet record showed the mode off with no PIN set, and the profile "
                 "record appeared in three different states. Values are reported as stored "
                 "and no meaning is assigned to the application's own field names.",
        "paths": ('*/system_handled/IndexedDB/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 147 rows",
        },
        "output_types": "standard",
        "artifact_icon": "database",
    },
    "ford_vehicle_capabilities": {
        "name": "Vehicle Capability Values",
        "description": "The last value the head unit cached for each of its internal HMI "
                       "topics, which record the equipment and configuration the vehicle "
                       "reported.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the topic map the HMI applications keep in IndexedDB, read with the "
                 "vendored ccl_chromium_indexeddb reader. Each row is one topic and the "
                 "last value cached against it, deduplicated across applications because "
                 "several applications cache the same topic. On the tested image these were "
                 "overwhelmingly equipment flags, such as whether a camera view or a "
                 "climate feature is present, rather than a record of use, so this answers "
                 "what the vehicle was built with rather than what was done in it. One "
                 "value on the tested image was live telemetry rather than a capability. "
                 "Topics and values are reported as stored, and the records carry no "
                 "timestamp, so when a value was cached is not established.",
        "paths": ('*/system_handled/IndexedDB/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 153 rows",
        },
        "output_types": "standard",
        "artifact_icon": "settings",
    },
}

import json
import os
import pathlib

from scripts.ccl import ccl_chromium_indexeddb
from scripts.ilapfuncs import artifact_processor

# Styling only, and its records can reference blobs an extraction may not carry.
_SKIP_DATABASES = {'THEME_PERSIST'}
_TOPIC_DATABASE = 'MQTT_API_TOPIC_MAP'
# The topic map also holds the theme worker's own cache entry, whose value is a
# raw byte run rather than a capability value. It is excluded so the artifact
# holds only what its description promises.
_TOPIC_EXCLUDE_PREFIX = 'com.ford.sdk__customStorage'
# The reader raises a wide range of types on a truncated or blob-backed record.
_READ_ERRORS = (ValueError, TypeError, KeyError, IndexError, OSError,
                NotImplementedError, StopIteration, AttributeError)


def _store_dirs(context):
    """Every IndexedDB leveldb directory the seeker matched."""
    found = set()
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        parent = os.path.dirname(file_found)
        if parent.endswith('.leveldb'):
            found.add(parent)
    return sorted(found)


def _application(store_dir):
    """The application directory name, which is not at a fixed depth."""
    app = ''
    for part in store_dir.replace('\\', '/').split('/'):
        if '.' in part and not part.startswith('.') and not part.endswith('.leveldb'):
            app = part
    return app or os.path.basename(os.path.dirname(store_dir))


def _as_text(value):
    """A stored value rendered for the report, without interpreting it."""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, default=str, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)
    return '' if value is None else str(value)


def _iter_records(store_dir):
    """Yield (database, object store, key, value) for one store."""
    try:
        wrapped = ccl_chromium_indexeddb.WrappedIndexDB(pathlib.Path(store_dir))
    except _READ_ERRORS:
        return
    try:
        for database_id in wrapped.database_ids:
            try:
                database = wrapped[database_id.dbid_no]
            except _READ_ERRORS:
                continue
            if database.name in _SKIP_DATABASES:
                continue
            for store_name in database.object_store_names:
                try:
                    store = database.get_object_store_by_name(store_name)
                    records = list(store.iterate_records())
                except _READ_ERRORS:
                    # A record whose blob is absent from the extraction ends
                    # the iteration; report what was read rather than nothing.
                    continue
                for record in records:
                    key = str(record.key)
                    # the reader renders a key as "<IdbKey value>"
                    if key.startswith('<IdbKey '):
                        key = key[len('<IdbKey '):].rstrip('>')
                    yield database.name, store_name, key, record.value
    finally:
        try:
            wrapped.close()
        except _READ_ERRORS:
            pass


@artifact_processor
def ford_hmi_app_state(context):
    data_list = []
    source_paths = []
    for store_dir in _store_dirs(context):
        app = _application(store_dir)
        rows = 0
        for db_name, store_name, key, value in _iter_records(store_dir):
            if db_name == _TOPIC_DATABASE:
                continue
            data_list.append((app, db_name, store_name, key, _as_text(value),
                              context.get_relative_path(store_dir)))
            rows += 1
        if rows:
            source_paths.append(store_dir)

    data_headers = ('Application', 'Database', 'Object Store', 'Key',
                    'Value (as stored)', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def ford_vehicle_capabilities(context):
    seen = {}
    source_paths = []
    for store_dir in _store_dirs(context):
        app = _application(store_dir)
        rows = 0
        for db_name, _store_name, key, value in _iter_records(store_dir):
            if db_name != _TOPIC_DATABASE or key.startswith(_TOPIC_EXCLUDE_PREFIX):
                continue
            # several applications cache the same topic; keep one row per topic
            if isinstance(value, dict) and 'value' in value:
                stored = _as_text(value.get('value'))
            else:
                stored = _as_text(value)
            seen.setdefault(key, (app, stored, store_dir))
            rows += 1
        if rows:
            source_paths.append(store_dir)

    data_list = [(topic, stored, app, context.get_relative_path(store_dir))
                 for topic, (app, stored, store_dir) in sorted(seen.items())]
    data_headers = ('Topic', 'Value (as stored)', 'First Seen In Application',
                    'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
