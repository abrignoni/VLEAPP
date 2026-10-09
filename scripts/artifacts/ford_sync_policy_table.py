"""Ford SYNC on Windows CE: policy table snapshots.

The module keeps JSON snapshots of the policy table its app-link component works from:

    Windows/syncP_Transfer/PolicyTableSnapShot_<number>

Each file is one JSON object with a policy_table member. Most of it is the policy itself,
which is the same text on every unit that received it: the functional groupings, the
default and device policies, the endpoints and the retry settings. Those parts are not
reported. What is reported is what the unit filled in: module_meta, the scalar values of
module_config, usage_and_error_counts, device_data and the per-application entries of
app_policies.

The key names are those of the open SmartDeviceLink policy table. No SmartDeviceLink
source was read for this module, so no key is given a meaning beyond its own name.
"""

import json
import os
import re

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "ford_sync_policy_table_values": {
        "name": "Ford SYNC WinCE - Policy Table Snapshot Values",
        "description": "Values the unit filled into its policy table snapshots: the module "
                       "identity and exchange counters, vehicle make, model and year, usage "
                       "and error counts for the module and for each application id, and the "
                       "device entries with their consent records.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC WinCE",
        "notes": "From Windows/syncP_Transfer/PolicyTableSnapShot_<number>, JSON files with "
                 "one policy_table object each. Tested on one unit read from its extracted "
                 "file set, a 2019 Ford Fusion (SYNC Gen1v5), which held 24 snapshots and gave "
                 "97 rows; no other tested Ford SYNC unit has the folder. The snapshots repeat "
                 "most values, so a value is reported once for each distinct combination of "
                 "section, key and value, with the number of snapshots holding it and the "
                 "lowest and highest file number among them: 54 rows were in all 24 files and "
                 "30 in one only. The counter that rose across the files was "
                 "module_meta.ignition_cycles_since_last_exchange, in step with the file "
                 "number; what the file number counts is not established. Reported sections "
                 "are module_meta, the scalar values of module_config, usage_and_error_counts, "
                 "device_data and the per-application entries of app_policies. The policy text "
                 "itself (functional groupings, the default and device policies, endpoints, "
                 "notification limits and retry settings) is left out because it is not the "
                 "unit's own state. The key names are those of the open SmartDeviceLink policy "
                 "table; no SmartDeviceLink source was read for this module, so a key means no "
                 "more here than its name says and values are shown as stored. Device entries "
                 "are keyed by a 64-character identifier, not by an address, and application "
                 "entries by a numeric id; neither is resolved to a name. A minutes or count "
                 "value is the unit's own tally. It does not establish who used the "
                 "application.",
        "paths": ('*/syncP_Transfer/PolicyTableSnapShot_*',),
        "sample_data": {
            "xtrmp_item010": "2013 Ford Escape, SYNC Gen1v3, extracted file set | 0 rows, no "
                             "syncP_Transfer folder",
            "xtrmp_item012": "2019 Ford Fusion, SYNC Gen1v5, extracted file set | 97 rows",
            "xtrmp_item014": "2014 Ford Edge SEL, SYNC Gen2, extracted file set | 0 rows, no "
                             "syncP_Transfer folder",
        },
        "output_types": "standard",
        "artifact_icon": "file-text",
    },
}

_SNAPSHOT_NAME = re.compile(r'PolicyTableSnapShot_(\d+)$')
# Policy text that is not the unit's own state.
_SKIPPED = (('functional_groupings',), ('consumer_friendly_messages',),
            ('app_policies', 'default'), ('app_policies', 'device'),
            ('module_config', 'endpoints'),
            ('module_config', 'notifications_per_minute_by_priority'),
            ('module_config', 'seconds_between_retries'))


def _leaves(value, path):
    """Yield (path, scalar) for every scalar under value, leaving out the policy text."""
    if path in _SKIPPED:
        return
    if isinstance(value, dict):
        if not value and path:
            yield path, '{}'
        for key in value:
            yield from _leaves(value[key], path + (str(key),))
    elif isinstance(value, list):
        for position, item in enumerate(value):
            yield from _leaves(item, path + (f'[{position}]',))
    else:
        yield path, value


def _shown(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


@artifact_processor
def ford_sync_policy_table_values(context):
    folded = {}
    source_paths = []
    for file_found in sorted({str(f) for f in context.get_files_found()}):
        named = _SNAPSHOT_NAME.search(os.path.basename(file_found))
        if not named or os.path.isdir(file_found):
            continue
        relative = context.get_relative_path(file_found)
        try:
            with open(file_found, 'rb') as handle:
                table = json.loads(handle.read().decode('utf-8'))['policy_table']
        except (OSError, ValueError, KeyError, TypeError):
            logfunc(f'Ford SYNC WinCE policy table: {relative} is not a policy table '
                    'snapshot this reader knows, not read')
            continue
        if not isinstance(table, dict):
            continue
        source_paths.append(file_found)
        number = int(named.group(1))
        folder = os.path.dirname(relative)
        for path, value in _leaves(table, ()):
            key = (folder, path[0], '.'.join(path[1:]), _shown(value))
            folded.setdefault(key, []).append(number)

    data_list = []
    for (folder, section, key, value), numbers in sorted(folded.items()):
        data_list.append((section, key, value, len(numbers), min(numbers), max(numbers),
                          folder))

    data_headers = ('Section', 'Key', 'Value', 'Snapshots With This Value',
                    'Lowest File Number', 'Highest File Number', 'Source Folder')
    return data_headers, data_list, '\n'.join(source_paths)
