__artifacts_v2__ = {
    "siriusxm_app_session_times": {
        "name": "SiriusXM App - Session Times",
        "description": "Times stored in the single-value files lastRebootTimeKey, "
                       "lastOnlineTimeKey and lastHeartbeatTime in the head unit's "
                       "persistence volume; what each time marks is taken from the file "
                       "name only.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "Each value is a whole file holding an integer, read as a Unix time in "
                 "milliseconds and divided by 1000. No source for the unit is cited; the "
                 "reading rests on the one comparison described below. These are times the "
                 "application wrote about itself; they are not a record of who was in the "
                 "vehicle. Two head units of different makes hold these files, a BMW MGU under "
                 "a folder named data_localStorage and a Ford SYNC 4 under "
                 "rwdata/sirius/emma/_localStorage, 3 rows on each. On the BMW image the "
                 "recorded online time fell 20 seconds after the containing ext4 filesystem's "
                 "own last mount time, so the two agree on the same start-up, but that "
                 "agreement was observed once and is not a general property.",
        "paths": ('*localStorage/private/shared/lastOnlineTimeKey',
                  '*localStorage/private/shared/lastRebootTimeKey',
                  '*localStorage/private/shared/lastHeartbeatTime'),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 3 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 3 rows",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
    },
    "siriusxm_app_account_and_device": {
        "name": "SiriusXM App - Account and Device",
        "description": "Values of eight single-value files (lastUserLoggedIn, "
                       "lastAvailableUsername, LastEpisodeDownloadUser, DeviceIdKey, "
                       "ClientDeviceIdKey, vehicle_info_metric_id, appRegion, freeToAir) in "
                       "the head unit's persistence volume.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.2",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "Values are reported as stored, with surrounding whitespace removed. Two head "
                 "units of different makes hold these files: a BMW MGU, 8 rows, and a Ford "
                 "SYNC 4, 8 rows, where vehicle_info_metric_id is written "
                 "vehicle_5Finfo_5Fmetric_5Fid. The file name is the application's own key "
                 "name; no meaning beyond that is asserted here. lastUserLoggedIn, "
                 "lastAvailableUsername and LastEpisodeDownloadUser held one 20 character "
                 "value, the same on both tested units of different makes, so it does not "
                 "identify an account on its own. DeviceIdKey, ClientDeviceIdKey and "
                 "vehicle_info_metric_id differed between the units; appRegion and freeToAir "
                 "did not. On the BMW image this store sat beside an eCryptfs-encrypted "
                 "subtree on the same volume, so an extraction of this volume may be only "
                 "partly readable. On the BMW image the store sat under a directory named "
                 "golden_package, which reads like a shipped default set, but it was the only "
                 "copy of this store present there and three of its values differed from the "
                 "other tested unit, so the name should not be taken to mean the contents are "
                 "factory defaults.",
        "paths": ('*localStorage/private/shared/lastUserLoggedIn',
                  '*localStorage/private/shared/lastAvailableUsername',
                  '*localStorage/private/shared/LastEpisodeDownloadUser',
                  '*localStorage/private/shared/DeviceIdKey',
                  '*localStorage/private/shared/ClientDeviceIdKey',
                  '*localStorage/private/shared/vehicle_info_metric_id',
                  '*localStorage/private/shared/vehicle_5Finfo_5Fmetric_5Fid',
                  '*localStorage/private/shared/appRegion',
                  '*localStorage/private/shared/freeToAir'),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 8 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 8 rows",
        },
        "output_types": "standard",
        "artifact_icon": "radio",
    },
    "siriusxm_app_recently_played": {
        "name": "SiriusXM App - Recently Played",
        "description": "Entries of the SiriusXM application's recently played lists, with the "
                       "start and end times each entry stores, its play, content and asset "
                       "types and the channel it names.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "From the SiriusXM application's local storage folder, which two tested head "
                 "units of different makes hold with the same file names: under "
                 "rwdata/sirius/emma/_localStorage on a Ford SYNC 4 and under a folder named "
                 "data_localStorage on a BMW MGU. On the Ford the names are written with _5F "
                 "for an underscore. Each file is one JSON document, and File Name is the "
                 "file's own name. Rows are the entries of the recentlyPlayeds list in the "
                 "files under private/user/<folder>/recentlyPlayedMap and "
                 "lastServerRecentsMap, where the folder had the same fixed name on both "
                 "tested units; Store names which. Start Date Time and End Date Time are the "
                 "entry's startDateTime and endDateTime, which carry a Z and are shown in UTC "
                 "to the whole second. startStreamDateTime and endStreamDateTime are a second "
                 "pair of times the entry stores, shown as stored: every one on the tested "
                 "units carried a +0000 offset. Of the 13 distinct entries with a "
                 "startDateTime, the stream start was identical on 5, within 15 milliseconds "
                 "on 4 and 2 to 37 minutes earlier on 4, and endStreamDateTime equalled "
                 "endDateTime on every entry that held both. What separates the two pairs is "
                 "not documented here. An entry can hold no times at all, and its time columns "
                 "are then empty. An entry can also hold an empty startDateTime with the other "
                 "times present (8 of 14 on the Ford); its Start Date Time is then empty. The "
                 "Ford gave 28 rows, the same 14 entries in each of the two stores; 6 of the "
                 "14 hold a startDateTime and 13 an endDateTime, from 2023-10-23 to "
                 "2024-03-27; the BMW gave 9 rows from two recentlyPlayedMap files, 7 dated, "
                 "from 2025-02-16 to 2026-02-26, and had no lastServerRecentsMap. Every entry "
                 "on both was of play type live and asset type channel, and none held a show "
                 "or episode title. A row records that the application stored that entry. It "
                 "does not establish who was listening.",
        "paths": ('*localStorage/private/user/*/recentlyPlayedMap/*',
                  '*localStorage/private/user/*/lastServerRecentsMap/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 28 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 9 rows",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
    },
    "siriusxm_app_favorites": {
        "name": "SiriusXM App - Favorites",
        "description": "Entries of the SiriusXM application's favorites lists, with the asset "
                       "name, type, channel id and short description each entry stores.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "From the SiriusXM application's local storage folder, which two tested head "
                 "units of different makes hold with the same file names: under "
                 "rwdata/sirius/emma/_localStorage on a Ford SYNC 4 and under a folder named "
                 "data_localStorage on a BMW MGU. On the Ford the names are written with _5F "
                 "for an underscore. Each file is one JSON document, and File Name is the "
                 "file's own name. Rows are the entries of the favoriteItemModels list in the "
                 "files under private/user/<folder>/favoritesListMap and lastFavoritesMap, "
                 "where the folder had the same fixed name on both tested units; Store names "
                 "which. Not reported: longDescription, the nested channel record, "
                 "satelliteId, comingledSortOrder, episodeCount, leagueId and teamId. The Ford "
                 "gave 10 rows, the same 5 assetGUIDs in each store, with a different short "
                 "description between the stores on 4 of them; the BMW gave 30, 15 in each, "
                 "and also held files with an empty document. No entry stores a time, so when "
                 "a favorite was set is not shown. A row records that the application stored "
                 "that favorite. It does not establish who chose it.",
        "paths": ('*localStorage/private/user/*/favoritesListMap/*',
                  '*localStorage/private/user/*/lastFavoritesMap/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 10 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 30 rows",
        },
        "output_types": "standard",
        "artifact_icon": "star",
    },
    "siriusxm_app_listener_profiles": {
        "name": "SiriusXM App - Listener Profiles",
        "description": "The listener profiles in the SiriusXM application's vehicle profile "
                       "file, with the first login and switch login times each stores and its "
                       "name, username and phone fields.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "From the SiriusXM application's local storage folder, which two tested head "
                 "units of different makes hold with the same file names: under "
                 "rwdata/sirius/emma/_localStorage on a Ford SYNC 4 and under a folder named "
                 "data_localStorage on a BMW MGU. On the Ford the names are written with _5F "
                 "for an underscore. Each file is one JSON document, and File Name is the "
                 "file's own name. Rows are the profile objects of the file under "
                 "private/user/<folder>/vehicleProfiles, where the folder had the same fixed "
                 "name as on the other tested unit, one per object that holds a gupId; Profile "
                 "Slot is the object's key in the document (activeListenerProfile and "
                 "defaultListenerProfile on the tested unit). The two times carry a Z and are "
                 "shown in UTC to the whole second. The Ford gave 2 rows, both with the same "
                 "gupId and the same two times, dated 2023-12-06, and with empty name, "
                 "username and phone fields. The BMW held no such file. What the application "
                 "means by first login and switch login is not documented here; the column "
                 "names are the stored keys.",
        "paths": ('*localStorage/private/user/*/vehicleProfiles/*/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 2 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 0 rows: no such file",
        },
        "output_types": "standard",
        "artifact_icon": "user",
    },
    "siriusxm_app_satellite_history": {
        "name": "SiriusXM App - Satellite Listening History",
        "description": "The SATRfyListeningHistory document of the SiriusXM application: its "
                       "lastTunedTime and its sidList.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "From the SiriusXM application's local storage folder, which two tested head "
                 "units of different makes hold with the same file names: under "
                 "rwdata/sirius/emma/_localStorage on a Ford SYNC 4 and under a folder named "
                 "data_localStorage on a BMW MGU. On the Ford the names are written with _5F "
                 "for an underscore. Each file is one JSON document, and File Name is the "
                 "file's own name. One row for each file under "
                 "public/user/<folder>/SATRfyListeningHistory, where the folder had the same "
                 "fixed name on both tested units. lastTunedTime is a 13-digit integer, read "
                 "as milliseconds since 1970 for Last Tuned Time and also shown as stored. No "
                 "source for the unit is cited: on the four tested files that reading falls in "
                 "the same months as the store's other times (2024-03 on the Ford, 2025-12 to "
                 "2026-03 on the BMW). sidList is a list of numbers, shown as stored; what a "
                 "sid identifies is not documented here. The Ford gave 1 row with 8 numbers; "
                 "the BMW gave 3 rows with 8, 1 and 2.",
        "paths": ('*localStorage/public/user/*/SATRfyListeningHistory/*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 1 row",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 3 rows",
        },
        "output_types": "standard",
        "artifact_icon": "radio",
    },
    "siriusxm_app_account_record": {
        "name": "SiriusXM App - Account Record",
        "description": "The values that are not empty in the SiriusXM application's "
                       "non_pii_information file, one row per key, with the key's path in the "
                       "document.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "SiriusXM App",
        "notes": "From the SiriusXM application's local storage folder, which two tested head "
                 "units of different makes hold with the same file names: under "
                 "rwdata/sirius/emma/_localStorage on a Ford SYNC 4 and under a folder named "
                 "data_localStorage on a BMW MGU. On the Ford the names are written with _5F "
                 "for an underscore. Each file is one JSON document, and File Name is the "
                 "file's own name. The file is private/shared/non_pii_information, holding a "
                 "getDeviceInformationNonPIIResponse object. Each value that is not empty is "
                 "reported with its dotted path as the key, as stored. On both tested units "
                 "the phone, email, last name, username and account number fields were empty, "
                 "and the values present were a first name, the first initial of a last name, "
                 "one subscription with its plan, a billing amount and a list of account "
                 "attributes: 36 rows on the Ford and 38 on the BMW. The object's name reads "
                 "as a service response; that reading is from the name only. The values are "
                 "not checked against anything here.",
        "paths": ('*localStorage/private/shared/non_pii_information',
                  '*localStorage/private/shared/non_5Fpii_5Finformation',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 36 rows",
            "bmw_mgu_2024_pers_logical": "BMW MGU, pers volume zip | 38 rows",
        },
        "output_types": "standard",
        "artifact_icon": "file-text",
    },
}

import json
import os
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, convert_unix_ts_to_utc, logdevinfo


def _read_value(file_found):
    """A stored value, or '' when the file is unreadable or empty."""
    try:
        with open(file_found, 'rb') as f:
            raw = f.read(4096)
    except OSError:
        return ''
    return raw.decode('utf-8', 'replace').strip()


@artifact_processor
def siriusxm_app_session_times(context):
    data_list = []
    source_paths = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        key = os.path.basename(file_found)
        value = _read_value(file_found)
        if not value:
            continue
        try:
            millis = int(value)
        except ValueError:
            continue
        # The unit is known to be milliseconds, so it is divided here rather
        # than handed to a helper that infers the unit from magnitude.
        timestamp = convert_unix_ts_to_utc(millis / 1000)
        source_paths.append(file_found)
        data_list.append((timestamp, key, value,
                          context.get_relative_path(file_found)))

    data_headers = (('Timestamp', 'datetime'), 'Key', 'Stored Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def siriusxm_app_account_and_device(context):
    data_list = []
    source_paths = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        key = os.path.basename(file_found)
        value = _read_value(file_found)
        if not value:
            continue
        source_paths.append(file_found)
        data_list.append((key, value, context.get_relative_path(file_found)))
        if key in ('DeviceIdKey', 'ClientDeviceIdKey', 'vehicle_info_metric_id',
                   'vehicle_5Finfo_5Fmetric_5Fid'):
            logdevinfo(f"SiriusXM {key}: {value}")

    data_headers = ('Key', 'Stored Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


def _documents(context):
    """(path, store folder, file name, parsed JSON) for each matched file that parses."""
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'rb') as handle:
                document = json.loads(handle.read().decode('utf-8', 'replace'))
        except (OSError, ValueError):
            continue
        yield (file_found, os.path.basename(os.path.dirname(file_found)),
               os.path.basename(file_found), document)


def _utc(text):
    """An ISO 8601 time with a zone, as UTC, or '' when it does not parse as one."""
    if not isinstance(text, str) or not text:
        return ''
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return ''
    if parsed.tzinfo is None:
        return ''
    return parsed.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def _text(value):
    """A stored value as text: '' for an absent one, JSON for a list or object."""
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


@artifact_processor
def siriusxm_app_recently_played(context):
    data_list = []
    source_paths = []
    for file_found, store, name, document in _documents(context):
        entries = document.get('recentlyPlayeds') if isinstance(document, dict) else None
        if not isinstance(entries, list):
            continue
        source_paths.append(file_found)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            data_list.append((
                _utc(entry.get('startDateTime')), _utc(entry.get('endDateTime')),
                _text(entry.get('startStreamDateTime')), _text(entry.get('endStreamDateTime')),
                _text(entry.get('recentPlayType')), _text(entry.get('contentType')),
                _text(entry.get('assetType')), _text(entry.get('channelGuid')),
                _text(entry.get('assetGUID')), _text(entry.get('assetName')),
                _text(entry.get('showTitle')), _text(entry.get('episodeTitle')),
                _text(entry.get('startStreamTime')), _text(entry.get('endStreamTime')),
                _text(entry.get('incognito')), _text(entry.get('gupId')),
                _text(entry.get('deviceGuid')), store, name))

    data_headers = (('Start Date Time', 'datetime'), ('End Date Time', 'datetime'),
                    'startStreamDateTime (as stored)', 'endStreamDateTime (as stored)',
                    'Recent Play Type', 'Content Type', 'Asset Type', 'Channel GUID',
                    'Asset GUID', 'Asset Name', 'Show Title', 'Episode Title',
                    'startStreamTime (as stored)', 'endStreamTime (as stored)', 'Incognito',
                    'gupId', 'Device GUID', 'Store', 'File Name')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def siriusxm_app_favorites(context):
    data_list = []
    source_paths = []
    for file_found, store, name, document in _documents(context):
        entries = document.get('favoriteItemModels') if isinstance(document, dict) else None
        if not isinstance(entries, list):
            continue
        source_paths.append(file_found)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            data_list.append((
                _text(entry.get('assetName')), _text(entry.get('assetType')),
                _text(entry.get('contentType')), _text(entry.get('channelId')),
                _text(entry.get('shortDescription')), _text(entry.get('assetGUID')),
                _text(entry.get('tabSortOrder')), _text(entry.get('globalSortOrder')),
                store, name))

    data_headers = ('Asset Name', 'Asset Type', 'Content Type', 'Channel ID',
                    'Short Description', 'Asset GUID', 'tabSortOrder (as stored)',
                    'globalSortOrder (as stored)', 'Store', 'File Name')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def siriusxm_app_listener_profiles(context):
    data_list = []
    source_paths = []
    for file_found, _store, name, document in _documents(context):
        if not isinstance(document, dict):
            continue
        found = False
        for slot in sorted(document):
            profile = document[slot]
            if not isinstance(profile, dict) or 'gupId' not in profile:
                continue
            found = True
            data_list.append((
                _utc(profile.get('firstLoginTimeStamp')),
                _utc(profile.get('switchLoginTimeStamp')), slot,
                _text(profile.get('profileName')), _text(profile.get('username')),
                _text(profile.get('phone')), _text(profile.get('gupId')),
                _text(profile.get('isActive')), _text(profile.get('isDefault')),
                _text(document.get('oemId')), name))
        if found:
            source_paths.append(file_found)

    data_headers = (('First Login Time', 'datetime'), ('Switch Login Time', 'datetime'),
                    'Profile Slot', 'Profile Name', 'Username', 'Phone', 'gupId', 'Is Active',
                    'Is Default', 'oemId', 'File Name')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def siriusxm_app_satellite_history(context):
    data_list = []
    source_paths = []
    for file_found, _store, name, document in _documents(context):
        if not isinstance(document, dict) or 'sidList' not in document:
            continue
        source_paths.append(file_found)
        stored = document.get('lastTunedTime')
        tuned = ''
        if isinstance(stored, int) and not isinstance(stored, bool) and stored > 0:
            # read as milliseconds since 1970, as the session keys of this store are
            tuned = convert_unix_ts_to_utc(stored / 1000)
        data_list.append((tuned, _text(stored), _text(document.get('sidList')), name))

    data_headers = (('Last Tuned Time', 'datetime'), 'lastTunedTime (as stored)',
                    'sidList (as stored)', 'File Name')
    return data_headers, data_list, '\n'.join(source_paths)


def _flatten(value, prefix=''):
    """(dotted key, text) for every value in a JSON document that is not empty."""
    if isinstance(value, dict):
        for key in value:
            yield from _flatten(value[key], f'{prefix}.{key}' if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten(item, f'{prefix}[{index}]')
    elif value not in ('', None):
        yield prefix, _text(value)


@artifact_processor
def siriusxm_app_account_record(context):
    data_list = []
    source_paths = []
    for file_found, _store, name, document in _documents(context):
        rows = [(key, value, name) for key, value in _flatten(document)]
        if not rows:
            continue
        source_paths.append(file_found)
        data_list.extend(rows)

    data_headers = ('Key', 'Stored Value', 'File Name')
    return data_headers, data_list, '\n'.join(source_paths)

