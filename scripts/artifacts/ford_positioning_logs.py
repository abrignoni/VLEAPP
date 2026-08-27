__artifacts_v2__ = {
    "ford_positioning_fixes": {
        "name": "Positioning Log Coordinates",
        "description": "Latitude and longitude values the head unit's positioning service "
                       "wrote to its own log, with the stage of the positioning chain each "
                       "one came from.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From fdplog.np.txt, the same log the GPS speed artifact reads. That "
                 "artifact parses only the dead reckoning lines, which carry speed and "
                 "heading and no coordinates; these are the other lines in the same file, "
                 "which do carry coordinates. Four line shapes are read and the Source "
                 "column says which produced each row, because they are not equivalent: "
                 "Raw GPS and UbloxReader are receiver output, Trimble Input is what was "
                 "fed to the fusion engine, and Trimble Output is what the engine returned. "
                 "The Result column is reported as stored, and on the tested image every "
                 "Trimble Output line recorded Failure, so those rows should not be read as "
                 "confirmed fixes. A coordinate in a service log is a value the software "
                 "handled; establishing that the vehicle was at that point is the "
                 "examiner's finding, not this artifact's. Timestamps carry an explicit Z "
                 "offset in the log and are taken as UTC on that basis.",
        "paths": ('*/*fdplog.np.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 109 rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "ford_nav_search_events": {
        "name": "Navigation Analytics Events",
        "description": "Events the navigation interface recorded in its analytics log, "
                       "with the phase reached, the attributes in effect and the "
                       "identifiers it assigned.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "From the hmi.analytics lines in fdplog.vn.txt. Each event spans several "
                 "consecutive lines sharing a thread id: a name and phase, an attributes "
                 "line, and a line naming the fields the application withheld. Those "
                 "withheld fields are reported by name in the Redacted Fields column and "
                 "their values are not in the log: the application logged the field names "
                 "and redacted the coordinates itself, so no position can be recovered "
                 "here. Attributes are reported as stored. On the tested image the events "
                 "spanned 53 seconds of one session, which bounds what this artifact can "
                 "show to whatever the log still held rather than to the life of the "
                 "vehicle.",
        "paths": ('*/*fdplog.vn.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 256 rows",
        },
        "output_types": "standard",
        "artifact_icon": "search",
    },
}

import re
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, get_file_path

# RFC5424 syslog: <PRI>V TIMESTAMP HOST APP PROCID MSGID [meta ...][fdp@... tid="N"] body
_LINE = re.compile(r'^<\d+>\d+\s+(\S+)\s+.*?\[fdp@[^\]]*tid="(\d+)"\]\s*(.*)$')
_NUM = r'(-?\d{1,3}\.\d{4,})'
# The four shapes that carry a coordinate, each naming a different stage.
_COORD_SHAPES = (
    ('Raw GPS', re.compile(r'Raw GPS:\s*latitude=\s*' + _NUM + r',\s*longitude=\s*' + _NUM)),
    ('UbloxReader', re.compile(r'UbloxReader:\s*lat\s*=\s*' + _NUM + r',\s*lon\s*=\s*' + _NUM)),
    ('Trimble Input', re.compile(r'Trimble Input\s+lat=' + _NUM + r',\s*lon=' + _NUM)),
    ('Trimble Output', re.compile(r'Trimble Output\s+.*?lat=' + _NUM + r',\s*lon=' + _NUM)),
)
_ALT = re.compile(r'alt=' + _NUM)
_HEADING = re.compile(r'heading\s*=\s*' + _NUM)
_RESULT = re.compile(r'res=(\w+)')
_ANALYTICS = re.compile(r'hmi\.analytics:\s*(.*)$')
_EVENT = re.compile(r'-+\[\s*(.*?)\s*\]-+\(\s*(.*?)\s*\)-+')
_REDACTED = re.compile(r'PII Attributes \(PII redacted\):\s*(.*)$')
_ATTRIBUTES = re.compile(r'Attributes:\s*(.*)$')


def _parse_line(line):
    """(timestamp, thread id, body) for a syslog line, or None."""
    match = _LINE.match(line)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def _timestamp(raw):
    """The log's ISO time, which carries an explicit Z, as a UTC datetime."""
    try:
        cleaned = raw.replace('Z', '+00:00')
        return datetime.fromisoformat(cleaned).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _read(context, filename):
    """The log's lines and its relative path."""
    source_path = get_file_path(context.get_files_found(), filename)
    if not source_path:
        return [], ''
    try:
        with open(source_path, 'r', encoding='utf-8', errors='replace') as handle:
            return handle.read().splitlines(), context.get_relative_path(source_path)
    except OSError:
        return [], context.get_relative_path(source_path)


@artifact_processor
def ford_positioning_fixes(context):
    data_list = []
    lines, relative_path = _read(context, "fdplog.np.txt")
    for line in lines:
        parsed = _parse_line(line)
        if not parsed:
            continue
        raw_time, _tid, body = parsed
        for source, pattern in _COORD_SHAPES:
            hit = pattern.search(body)
            if not hit:
                continue
            altitude = _ALT.search(body)
            heading = _HEADING.search(body)
            result = _RESULT.search(body)
            data_list.append((_timestamp(raw_time), float(hit.group(1)),
                              float(hit.group(2)),
                              altitude.group(1) if altitude else '',
                              heading.group(1) if heading else '',
                              source, result.group(1) if result else '',
                              relative_path))
            break

    data_headers = (('Timestamp', 'datetime'), 'Latitude', 'Longitude',
                    'Altitude (as stored)', 'Heading (as stored)', 'Source',
                    'Result (as stored)', 'Source File')
    return data_headers, data_list, relative_path


@artifact_processor
def ford_nav_search_events(context):
    data_list = []
    lines, relative_path = _read(context, "fdplog.vn.txt")
    # An event is a run of hmi.analytics lines on one thread: the name and
    # phase first, then its attributes and the fields the app withheld.
    current = None
    for line in lines:
        parsed = _parse_line(line)
        if not parsed:
            continue
        raw_time, tid, body = parsed
        analytics = _ANALYTICS.search(body)
        if not analytics:
            continue
        payload = analytics.group(1).strip()

        event = _EVENT.search(payload)
        if event:
            if current:
                data_list.append(current)
            current = [_timestamp(raw_time), event.group(1), event.group(2),
                       '', '', tid, relative_path]
            continue
        if current is None:
            continue
        attributes = _ATTRIBUTES.match(payload)
        if attributes:
            current[3] = attributes.group(1).strip()
            continue
        redacted = _REDACTED.match(payload)
        if redacted:
            current[4] = redacted.group(1).strip()
    if current:
        data_list.append(current)

    data_headers = (('Timestamp', 'datetime'), 'Event', 'Phase',
                    'Attributes (as stored)', 'Redacted Fields', 'Thread',
                    'Source File')
    return data_headers, [tuple(row) for row in data_list], relative_path
