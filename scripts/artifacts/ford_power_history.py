__artifacts_v2__ = {
    "ford_power_last_shutdown": {
        "name": "Ford SYNC 4 - Last Shutdown",
        "description": "The shutdown the head unit recorded most recently, with the boot "
                       "count, the time, the uptime for that cycle and the initiator and "
                       "reason it stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From last-shutdown.txt, a file that held a single record on the tested "
                 "image. real time is read as a Unix time in milliseconds and divided by "
                 "1000. On ford_syncg4_logical that reading and the record's up-time, taken "
                 "as milliseconds, fall within 1 millisecond of the clock reading and "
                 "up-time on the smlog.1 line for the same boot count in the same folder. "
                 "up-time and total up-time are reported as stored. On the tested "
                 "image this record sat one boot count ahead of the last block in "
                 "reset-history.txt, which shows the history file did not include the most "
                 "recent cycle.",
        "paths": ('*/fordlogs/sm/last-shutdown.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "power",
    },
    "ford_power_reset_reason": {
        "name": "Ford SYNC 4 - Last Reset Reason",
        "description": "The reset the head unit recorded most recently in its own reset "
                       "reason file, with the boot count, the time, and the initiator and "
                       "reason it stored.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-27",
        "last_update_date": "2026-08-27",
        "requirements": "none",
        "category": "Ford SYNC 4",
        "notes": "From reset-reason.txt, a file that held a single record on the tested "
                 "image. Same field vocabulary as last-shutdown.txt, and real time is read "
                 "the same way, as milliseconds divided by 1000. On the tested image this "
                 "record named a reset at a much lower boot count than the current one, so "
                 "the file does not necessarily describe the most recent power cycle. On the "
                 "tested image its timestamp fell 22 seconds before the first settings "
                 "write in the navigation application's own store, which is one observation. "
                 "Initiator and reason are reported as stored.",
        "paths": ('*/fordlogs/sm/reset-reason.txt',),
        "sample_data": {
            "ford_syncg4_logical": "Ford Sync G4 | 1 row",
        },
        "output_types": "standard",
        "artifact_icon": "rotate-ccw",
    },
}


from scripts.ilapfuncs import (artifact_processor, convert_unix_ts_to_utc,
                               get_file_path)


def _single_record(context, filename):
    """The one key/value record these single-cycle files hold, or None."""
    source_path = get_file_path(context.get_files_found(), filename)
    if not source_path:
        return None, ''
    try:
        with open(source_path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    except OSError:
        return None, context.get_relative_path(source_path)
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(':')
        if sep:
            fields[key.strip()] = value.strip()
    return fields, context.get_relative_path(source_path)


def _power_row(fields):
    """One row, shared by last-shutdown.txt and reset-reason.txt."""
    try:
        # The unit is known to be milliseconds, so it is divided here rather
        # than handed to a helper that infers the unit from magnitude.
        stamp = convert_unix_ts_to_utc(int(fields.get('real time', '')) / 1000)
    except ValueError:
        stamp = None
    return (stamp, fields.get('boot count', ''), fields.get('initiator', ''),
            fields.get('reason', ''), fields.get('up-time', ''),
            fields.get('total up-time', ''))


_POWER_HEADERS = (('Timestamp', 'datetime'), 'Boot Count', 'Initiator', 'Reason',
                  'Up Time (as stored)', 'Total Up Time (as stored)')


@artifact_processor
def ford_power_last_shutdown(context):
    fields, relative_path = _single_record(context, "last-shutdown.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields)], relative_path


@artifact_processor
def ford_power_reset_reason(context):
    fields, relative_path = _single_record(context, "reset-reason.txt")
    if not fields:
        return (), [], relative_path
    return _POWER_HEADERS, [_power_row(fields)], relative_path
