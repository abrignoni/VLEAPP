__artifacts_v2__ = {
    "ford_positioning_fixes": {
        "name": "Ford SYNC 4 - Positioning Log Coordinates",
        "description": "Latitude and longitude values the head unit's positioning service "
                       "wrote to its own log, with the label of the log line each "
                       "one came from.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-04",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From every file the paths pattern matches: fdplog.np.txt and its rotated "
                 "and pre_ copies. A file whose bytes equal a file already read is "
                 "skipped, and the Source File column names the file each row came from. "
                 "On the tested image three files matched, two of them byte identical, "
                 "and the rows came from fdplog.np.txt (109) and pre_fdplog.np.txt.0 "
                 "(105). The GPS speed artifact reads the same files. That "
                 "artifact parses only the dead reckoning lines, which carry speed and "
                 "heading and no coordinates; these are the other lines in the same files, "
                 "which do carry coordinates. Four line shapes are read and the Source "
                 "column carries the label on the log line (Raw GPS, UbloxReader, Trimble "
                 "Input or Trimble Output). What stage each label stands for is not "
                 "established here. "
                 "The Result column is reported as stored, and on the tested image 81 of "
                 "the 82 Trimble Output rows recorded Failure and 1 recorded Success, so a "
                 "Trimble Output row is not by itself a confirmed fix. A coordinate in a service log is a value the software "
                 "handled; establishing that the vehicle was at that point is the "
                 "examiner's finding, not this artifact's. Timestamps carry an explicit Z "
                 "offset in the log and are taken as UTC on that basis.",
        "paths": ('*/*fdplog.np.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 214 rows",
        },
        "output_types": "all",
        "artifact_icon": "map-pin",
    },
    "ford_nav_search_events": {
        "name": "Ford SYNC 4 - Navigation Analytics Events",
        "description": "Events from hmi.analytics lines in the head unit's "
                       "fdplog.vn.txt logs, each with its phase, attributes, redacted field "
                       "names and thread id.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-10-04",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From the hmi.analytics lines in every file the paths pattern matches: "
                 "fdplog.vn.txt and its rotated and pre_ copies. A file whose bytes equal "
                 "a file already read is skipped, and the Source File column names the "
                 "file each row came from. On the tested image four files matched, two of "
                 "them byte identical, and the rows came from fdplog.vn.txt (256), "
                 "fdplog.vn.txt.0 (254) and pre_fdplog.vn.txt.0 (258). Each event is "
                 "read as a name and phase line, then the attributes line and the line "
                 "naming withheld fields that follow it under the same thread id in that "
                 "file. On the tested image every row carried one thread id, so lines from "
                 "two threads interleaving was exercised only on a constructed file. The "
                 "withheld fields are "
                 "reported by name in the Redacted Fields column: the log line is "
                 "labelled \"PII Attributes (PII redacted)\" and lists field names without "
                 "values, so the withheld values cannot be recovered from this log. "
                 "Attributes are reported as stored. On the tested image the events "
                 "spanned about 46 hours, so this artifact shows what the logs still "
                 "held, not the life of the vehicle.",
        "paths": ('*/*fdplog.vn.txt*',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 768 rows",
        },
        "output_types": "standard",
        "artifact_icon": "search",
    },
}

import hashlib
import os
import re
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor

# RFC5424 syslog: <PRI>V TIMESTAMP HOST APP PROCID MSGID [meta ...][fdp@... tid="N"] body
_LINE = re.compile(r'^<\d+>\d+\s+(\S+)\s+.*?\[fdp@[^\]]*tid="(\d+)"\]\s*(.*)$')
_NUM = r'(-?\d{1,3}\.\d{4,})'
# The four shapes that carry a coordinate, each with the label its line carries.
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


def _read(context):
    """(lines, relative path) for each matched log, in path order.

    The paths pattern also matches the rotated and pre_ copies of the log. A
    file whose bytes equal a file already read is skipped, so a copy adds no
    rows.
    """
    logs = []
    seen = set()
    for source_path in sorted(str(found) for found in context.get_files_found()):
        if os.path.isdir(source_path):
            continue
        try:
            with open(source_path, 'rb') as handle:
                content = handle.read()
        except OSError:
            continue
        digest = hashlib.sha256(content).digest()
        if digest in seen:
            continue
        seen.add(digest)
        logs.append((content.decode('utf-8', errors='replace').splitlines(),
                     context.get_relative_path(source_path)))
    return logs


@artifact_processor
def ford_positioning_fixes(context):
    data_list = []
    logs = _read(context)
    for lines, relative_path in logs:
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
    return data_headers, data_list, '\n'.join(path for _lines, path in logs)


@artifact_processor
def ford_nav_search_events(context):
    data_list = []
    logs = _read(context)
    for lines, relative_path in logs:
        # An event is the name and phase line, then the attributes line and
        # the withheld fields line that follow it on the same thread id. Rows
        # stay in the order of their name and phase lines.
        open_events = {}
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
                current = [_timestamp(raw_time), event.group(1), event.group(2),
                           '', '', tid, relative_path]
                data_list.append(current)
                open_events[tid] = current
                continue
            current = open_events.get(tid)
            if current is None:
                continue
            attributes = _ATTRIBUTES.match(payload)
            if attributes:
                current[3] = attributes.group(1).strip()
                continue
            redacted = _REDACTED.match(payload)
            if redacted:
                current[4] = redacted.group(1).strip()

    data_headers = (('Timestamp', 'datetime'), 'Event', 'Phase',
                    'Attributes (as stored)', 'Redacted Fields', 'Thread',
                    'Source File')
    return (data_headers, [tuple(row) for row in data_list],
            '\n'.join(path for _lines, path in logs))
