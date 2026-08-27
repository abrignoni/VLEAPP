__artifacts_v2__ = {
    "ford_hmi_localstorage": {
        "name": "HMI Local Storage",
        "description": "Values the head unit's HMI applications stored in Chromium Local "
                       "Storage, with the time each write batch was recorded. Superseded "
                       "versions of a key are reported alongside the current one.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "The HMI applications are Chromium based and keep their state in Local "
                 "Storage, which is a LevelDB store. It is read here with the vendored "
                 "ccl_leveldb reader rather than by scanning the files, because LevelDB "
                 "table blocks are Snappy compressed and a byte scan cannot see them, "
                 "cannot recover the key a value belonged to, and cannot tell a live record "
                 "from a superseded one. Timestamps come from the store's own META records, "
                 "which hold a Chrome epoch in microseconds, and apply to the write batch "
                 "rather than to the individual key. Every version of a key is reported, "
                 "not only the current one, so the same key appears once per batch that "
                 "wrote it and the Live column says which is current. On the tested image "
                 "one application held 30 versions of its profile list spanning 2023-05-22 "
                 "to 2024-03-27, and the values differ between versions. What changed "
                 "between two versions is left to the examiner rather than diffed here. "
                 "Values are reported as stored: the setting names are the application's "
                 "own and their integers are undocumented. A stored value records what was "
                 "written and when; it does not establish who was in the vehicle.",
        "paths": ('*/system_handled/Local Storage/leveldb/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 35 rows",
        },
        "output_types": "standard",
        "artifact_icon": "database",
    },
}

import os
import struct

from scripts.ccl import ccl_leveldb
from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc

_META_PREFIX = b'META:'
# Chromium writes Local Storage values with a one byte encoding marker.
_UTF16_MARKER = 0
# Seconds between the Windows/Chrome epoch (1601-01-01) and the Unix epoch.
_CHROME_EPOCH_OFFSET = 11644473600


def _decode_value(raw):
    """A Local Storage value, decoded by its own leading encoding marker."""
    if not raw:
        return ''
    if raw[0] == _UTF16_MARKER:
        return raw[1:].decode('utf-16-le', 'replace')
    return raw[1:].decode('utf-8', 'replace')


def _meta_timestamp(raw):
    """The Chrome timestamp out of a META record's protobuf, or None.

    Field 1 is a varint holding microseconds since 1601-01-01.
    """
    if not raw or raw[0] != 0x08:            # field 1, varint
        return None
    value = shift = 0
    for byte in raw[1:]:
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return convert_unix_ts_to_utc(value / 1000000 - _CHROME_EPOCH_OFFSET)
        shift += 7
    return None


@artifact_processor
def ford_hmi_localstorage(context):
    data_list = []
    source_paths = []
    # The reader needs the store directory, so collapse the matched files to it.
    store_dirs = set()
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        store_dirs.add(os.path.dirname(file_found))

    for store_dir in sorted(store_dirs):
        try:
            store = ccl_leveldb.RawLevelDb(store_dir)
            records = list(store.iterate_records_raw())
        except (OSError, ValueError, struct.error, NotImplementedError):
            continue
        source_paths.append(store_dir)

        # META records carry the batch time; a value record belongs to the
        # newest batch at or below its own sequence number.
        batches = sorted(
            (r.seq, _meta_timestamp(r.value))
            for r in records
            if r.user_key.startswith(_META_PREFIX) and r.state == ccl_leveldb.KeyState.Live)

        def _batch_time(seq, _batches=batches):
            stamp = None
            for batch_seq, batch_time in _batches:
                if batch_seq <= seq:
                    stamp = batch_time
                else:
                    break
            return stamp

        # The application directory is not at a fixed depth: the HMI apps sit
        # directly above system_handled while the packaged apps add a user-data
        # level. Anchor on the package-style name instead of counting levels.
        app = ''
        for part in store_dir.replace('\\', '/').split('/'):
            if '.' in part and not part.startswith('.'):
                app = part
        if not app:
            app = os.path.basename(os.path.dirname(store_dir))
        for record in records:
            key = record.user_key
            if key.startswith(_META_PREFIX) or not key.startswith(b'_'):
                continue
            storage_key, _, script_key = key[1:].partition(b'\x00')
            if not script_key:
                continue
            # The script key carries its own encoding marker, like the value.
            script_key = _decode_value(script_key)
            data_list.append((
                _batch_time(record.seq), app,
                storage_key.decode('utf-8', 'replace'), script_key,
                _decode_value(record.value),
                record.state == ccl_leveldb.KeyState.Live,
                record.seq, os.path.basename(record.origin_file),
                context.get_relative_path(store_dir)))
        store.close()

    data_list.sort(key=lambda row: (row[1], row[3], row[6]))
    data_headers = (('Batch Written', 'datetime'), 'Application', 'Storage Key',
                    'Key', 'Value (as stored)', 'Live', 'Sequence',
                    'Store File', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
