__artifacts_v2__ = {
    "bmw_sxm_session": {
        "name": "SiriusXM Session Times",
        "description": "Times the SiriusXM application recorded for its own last reboot, "
                       "last online connection and last heartbeat, read from single-value "
                       "files in the head unit's persistence volume.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "BMW Vehicles",
        "notes": "Each value is stored as a whole file holding a Unix time in milliseconds, "
                 "converted here by dividing by 1000 at the call site because the unit is "
                 "known rather than inferred from magnitude. These are times the application "
                 "wrote about itself; they are not a record of who was in the vehicle. On the "
                 "one tested image the recorded online time fell 20 seconds after the "
                 "containing ext4 filesystem's own last mount time, so the two agree on the "
                 "same start-up, but that agreement was observed once and is not a general "
                 "property.",
        "paths": ('*/data_localStorage/private/shared/lastOnlineTimeKey',
                  '*/data_localStorage/private/shared/lastRebootTimeKey',
                  '*/data_localStorage/private/shared/lastHeartbeatTime'),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "2024 BMW MGU | SiriusXM app state | 3 rows",
        },
        "output_types": "standard",
        "artifact_icon": "clock",
    },
    "bmw_sxm_account": {
        "name": "SiriusXM Account and Device",
        "description": "Account and device identifiers the SiriusXM application stored in the "
                       "head unit's persistence volume, each as a single-value file.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "BMW Vehicles",
        "notes": "Values are reported as stored. The file name is the application's own key "
                 "name; no meaning beyond that is asserted here. lastUserLoggedIn and "
                 "lastAvailableUsername held the same 20 character value on the tested image, "
                 "which is one observation and not a rule. This store sits beside an "
                 "eCryptfs-encrypted subtree on the same volume, so an extraction of this "
                 "volume may be only partly readable.",
        "paths": ('*/data_localStorage/private/shared/lastUserLoggedIn',
                  '*/data_localStorage/private/shared/lastAvailableUsername',
                  '*/data_localStorage/private/shared/LastEpisodeDownloadUser',
                  '*/data_localStorage/private/shared/DeviceIdKey',
                  '*/data_localStorage/private/shared/ClientDeviceIdKey',
                  '*/data_localStorage/private/shared/vehicle_info_metric_id',
                  '*/data_localStorage/private/shared/appRegion',
                  '*/data_localStorage/private/shared/freeToAir'),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "2024 BMW MGU | SiriusXM app state | 8 rows",
        },
        "output_types": "standard",
        "artifact_icon": "radio",
    },
}

import os

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
def bmw_sxm_session(context):
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
def bmw_sxm_account(context):
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
        if key in ('DeviceIdKey', 'ClientDeviceIdKey', 'vehicle_info_metric_id'):
            logdevinfo(f"SiriusXM {key}: {value}")

    data_headers = ('Key', 'Stored Value', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
