"""Ford SYNC 4: selected lines of the platform log.

The module writes a rolling platform log, several megabytes a file, in which every
component logs:

    rwdata/logs/fdplog.<zone>.txt[.<n>]        the current files
    rwdata/logs/pre_fdplog.<zone>.txt[.<n>]    the files kept from before

A line is '<priority>1 <time>Z <host> <process> <pid> <component> [meta sequenceId="n"]
[...] <text>'. The time carries a Z. Almost all of the log is developer tracing, so this
module reports only the lines of two components whose text states something about use:
the charge location lines of evChargeSettings and the search events of the navigation
analytics. Files with identical content are read once.
"""

import hashlib
import os
import re
from datetime import datetime

from scripts.ilapfuncs import artifact_processor

__artifacts_v2__ = {
    "ford_sync4_charge_locations": {
        "name": "Ford SYNC 4 - Charge Locations In Log",
        "description": "Charge locations named in the platform log's charge settings lines: "
                       "the list the line belongs to, the location id and the latitude and "
                       "longitude it carries, with the first and last time each was logged.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their "
                 "numbered copies, the module's rolling platform log. Almost all of it is "
                 "developer tracing from several hundred components; this artifact reads one "
                 "component's lines and leaves the rest. Files with identical content are read "
                 "once. Tested on one Ford SYNC 4 unit read from its logical zip, where the "
                 "log covered 2024-03-27 to 2024-03-29. Each line's time carries a Z and is "
                 "reported as the line states it; a 1970 time, written before the clock was "
                 "set, is left empty. The log is a rolling window, so it holds only what was "
                 "logged in the days before the extraction. Rows come from the "
                 "evChargeSettings lines 'handleSavedChargeLocationMsg' and "
                 "'handleUnsavedChargeLocationMsg', which carry a location id and two whole "
                 "numbers. Identical values are folded into one row with the number of lines "
                 "and the first and last log time: 259 lines gave 21 rows, 11 from the saved "
                 "list and 10 from the unsaved list. The numbers are degrees times 1,000,000: "
                 "three decimal coordinate pairs the same component logged elsewhere equal "
                 "three of these pairs divided by that. Four rows, all from the unsaved list, "
                 "held a position; the other 17 held 128048575 and 256048575 or zeros, which "
                 "are outside the range of a coordinate and read as an empty slot, so their "
                 "Latitude and Longitude are left empty and the stored numbers are still "
                 "shown. What the module means by saved and unsaved is not documented here; "
                 "the names are the log's own. The address fields in the related lines were "
                 "empty on every tested line and are not reported. A row records that the "
                 "module logged that location for the vehicle's charge settings. It does not "
                 "establish when the vehicle was there.",
        "paths": ('*/rwdata/logs/*fdplog*.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 21 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
    "ford_sync4_nav_searches": {
        "name": "Ford SYNC 4 - Navigation Searches In Log",
        "description": "Navigation searches named in the platform log's analytics lines, one "
                       "row per search id, with the search type and options, the number of "
                       "result lines, the provider and the logged duration.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From rwdata/logs/fdplog.<zone>.txt and pre_fdplog.<zone>.txt with their "
                 "numbered copies, the module's rolling platform log. Almost all of it is "
                 "developer tracing from several hundred components; this artifact reads one "
                 "component's lines and leaves the rest. Files with identical content are read "
                 "once. Tested on one Ford SYNC 4 unit read from its logical zip, where the "
                 "log covered 2024-03-27 to 2024-03-29. Each line's time carries a Z and is "
                 "reported as the line states it; a 1970 time, written before the clock was "
                 "set, is left empty. The log is a rolling window, so it holds only what was "
                 "logged in the days before the extraction. Rows come from the navigation "
                 "application's analytics lines: a header naming the event (search started, "
                 "resultFound or complete) followed by a line of attributes. They are grouped "
                 "on the search id: 761 event lines gave 30 rows, 23 with a start line and 7 "
                 "whose start had already rolled out of the log. The log states that the "
                 "position and text attributes are redacted, and they are: no search text, "
                 "result name or coordinate is in the file, so none is reported. What remains "
                 "is the search type (Coordinate 10, POI 7, Category 4, SavedPlace 2 on the "
                 "tested unit), the options, a POI category on three rows, the voice search "
                 "flag, the provider and the duration in milliseconds, all as stored. Result "
                 "Lines counts the resultFound lines for that search id, from 0 to 167. A row "
                 "records that the navigation application logged a search. It does not "
                 "establish what was searched for or who searched.",
        "paths": ('*/rwdata/logs/*fdplog*.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync 4, logical zip | 30 rows",
        },
        "output_types": "standard",
        "artifact_icon": "search",
    },
}

_LINE = re.compile(r'^<\d+>1 (\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.?\d*Z \S+ \S+ \S+ (\S+) '
                   r'\[meta sequenceId="\d+"\]\[[^\]]*\] ?(.*)$')
_CHARGE = re.compile(r'handle(Saved|Unsaved)ChargeLocationMsg: ChrgLocId_D_\w+: (\d+) '
                     r'ChrgLocLatt_An_\w+: (-?\d+) ChrgLocLong_An_\w+: (-?\d+)')
_ANALYTICS_HEAD = re.compile(r'hmi\.analytics: ---\[ (\w+) \]-----\( (\w+) \)---')
_ANALYTICS_ATTRS = re.compile(r'hmi\.analytics: Attributes: (.*)$')
_ATTR = re.compile(r'\[(\w+): ([^\]]*)\]')
_DEGREE = 1000000


def _log_lines(context):
    """(log time or '', component, text, relative path) for each line of each distinct file."""
    seen = set()
    for file_found in sorted(str(f) for f in set(context.get_files_found())):
        if os.path.isdir(file_found) or 'fdplog' not in os.path.basename(file_found):
            continue
        try:
            with open(file_found, 'rb') as handle:
                data = handle.read()
        except OSError:
            continue
        digest = hashlib.sha256(data).digest()
        if not data or digest in seen:
            continue
        seen.add(digest)
        relative = context.get_relative_path(file_found)
        for line in data.decode('utf-8', 'replace').split('\n'):
            match = _LINE.match(line)
            if not match:
                continue
            year, month, day, hour, minute, second = (int(v) for v in match.groups()[:6])
            stamp = ''
            if year != 1970:
                try:
                    stamp = datetime(year, month, day, hour, minute,
                                     second).strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    stamp = ''
            yield stamp, match.group(7), match.group(8), relative, file_found


@artifact_processor
def ford_sync4_charge_locations(context):
    found = {}
    sources = []
    for stamp, component, text, relative, path in _log_lines(context):
        if component != 'evChargeSettings':
            continue
        match = _CHARGE.search(text)
        if not match:
            continue
        key = (match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4)))
        entry = found.setdefault(key, ['', '', 0, relative])
        if stamp:
            entry[0] = min(entry[0], stamp) if entry[0] else stamp
            entry[1] = max(entry[1], stamp)
        entry[2] += 1
        if path not in sources:
            sources.append(path)

    data_list = []
    for (kind, number, latitude, longitude), (first, last, count, relative) in sorted(
            found.items()):
        in_range = abs(latitude) <= 90 * _DEGREE and abs(longitude) <= 180 * _DEGREE \
            and (latitude or longitude)
        data_list.append((first, last, kind, number,
                          latitude / _DEGREE if in_range else '',
                          longitude / _DEGREE if in_range else '',
                          latitude, longitude, count, relative))

    data_headers = (('First Log Time', 'datetime'), ('Last Log Time', 'datetime'), 'List',
                    'Location ID', 'Latitude', 'Longitude', 'Latitude (as stored)',
                    'Longitude (as stored)', 'Lines', 'First Source File')
    return data_headers, data_list, '\n'.join(sources)


@artifact_processor
def ford_sync4_nav_searches(context):
    searches = {}
    order = []
    sources = []
    pending = None
    for stamp, component, text, relative, path in _log_lines(context):
        if component != 'vendor.garmin' or 'hmi.analytics' not in text:
            continue
        head = _ANALYTICS_HEAD.search(text)
        if head:
            pending = (stamp, head.group(2)) if head.group(1) == 'search' else None
            continue
        attrs = _ANALYTICS_ATTRS.search(text)
        if not attrs or pending is None:
            continue
        values = dict(_ATTR.findall(attrs.group(1)))
        uid = values.get('searchUID', '').strip()
        when, action = pending
        pending = None
        if not uid:
            continue
        if uid not in searches:
            searches[uid] = {'started': '', 'completed': '', 'first result': '', 'results': 0,
                             'file': relative}
            order.append(uid)
        entry = searches[uid]
        if path not in sources:
            sources.append(path)
        if action == 'started':
            entry['started'] = when
            for name in ('searchType', 'searchOptions', 'isASRSearch', 'poiCategory'):
                entry[name] = values.get(name, '').strip()
        elif action == 'resultFound':
            entry['results'] += 1
            entry['first result'] = entry['first result'] or when
            entry['searchProvider'] = values.get('searchProvider', '').strip()
        elif action == 'complete':
            entry['completed'] = when
            entry['durationMs'] = values.get('durationMs', '').strip()

    data_list = []
    for uid in order:
        entry = searches[uid]
        data_list.append((entry['started'] or entry['first result'] or entry['completed'],
                          entry['completed'], entry.get('searchType', ''),
                          entry.get('searchOptions', ''), entry.get('poiCategory', ''),
                          entry.get('isASRSearch', ''), entry['results'],
                          entry.get('searchProvider', ''), entry.get('durationMs', ''),
                          'Yes' if entry['started'] else 'No', uid, entry['file']))

    data_headers = (('First Log Time', 'datetime'), ('Complete Log Time', 'datetime'),
                    'Search Type', 'Search Options', 'POI Category', 'Voice Search (as stored)',
                    'Result Lines', 'Search Provider', 'Duration Milliseconds (as stored)',
                    'Start Line Found', 'Search ID', 'First Source File')
    return data_headers, data_list, '\n'.join(sources)
