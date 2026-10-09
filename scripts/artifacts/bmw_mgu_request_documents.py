"""BMW MGU head unit: the request documents kept under hdshare/tm/dumm.

The folder holds one numbered entry per request. Most are two-byte files holding 'OK'.
The others are gzip-compressed JSON documents:

    hdshare/tm/dumm/<number>.gzip    one JSON object: position, vehicleCapabilities,
                                     dataPrivacySettings, requestReason, counter, ids, ...

A file is read only when it inflates to a JSON object that has a position member. The
document carries no time of its own.
"""

import gzip
import json
import os
import re
from datetime import datetime, timezone

from scripts.ilapfuncs import artifact_processor, logfunc

__artifacts_v2__ = {
    "bmw_mgu_request_documents": {
        "name": "BMW MGU - Request Documents",
        "description": "One row for each request document: the position it carries, the "
                       "request reason and counter, the mileage and position age bands, and "
                       "the software levels it states.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "BMW MGU",
        "notes": "From hdshare/tm/dumm/<number>.gzip, gzip-compressed JSON documents that sit "
                 "among several thousand two-byte files holding 'OK' in the same folder. A "
                 "file is read only when it inflates to a JSON object with a position member. "
                 "Tested on one BMW MGU unit read from the logical zip of its persistence "
                 "volume, which held 150 such documents numbered from 31 to 8,096. What "
                 "component writes them and where they are sent is not established here; the "
                 "folder and key names are all there is to go on. All 150 carried a position "
                 "marked valid, 63 distinct places between them, and the latitude and "
                 "longitude are reported as stored; a position not marked valid is left empty. "
                 "Altitude was -999 on 52 documents, which reads as not available, and is "
                 "shown as stored. Request Reason was LcResume on 124, PrivacyChange on 24 and "
                 "LcStartup on one, with one document lacking the key. The document holds no "
                 "time of its own. File Modified Time is filled only when the input records a "
                 "modified time for the file; the tested zip does not carry one in a form this "
                 "tool reads, so the column was empty on all 150 rows, and the zip entry's own "
                 "date is the place to look. The request number is not a reliable order: "
                 "sorted by it, the zip entries' dates rise from one document to the next on "
                 "107 of 149 pairs, and the counter on 107 of 148. Mileage Band and Position "
                 "Age Band are the document's own coded values, as stored. The documents also "
                 "carry the VIN, a list of option codes and component version lists, which are "
                 "not surfaced here. A row records that the unit wrote a document with that "
                 "position. It does not establish who was driving.",
        "paths": ('*/tm/dumm/*.gzip',),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "BMW MGU, logical zip | 150 rows",
        },
        "output_types": "standard",
        "artifact_icon": "map-pin",
    },
    "bmw_mgu_request_privacy_settings": {
        "name": "BMW MGU - Privacy Settings In Request Documents",
        "description": "The data privacy settings named in the request documents, one row for "
                       "each distinct setting and value, with how many documents carry it and "
                       "the lowest and highest request number among them.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-10-09",
        "last_update_date": "2026-10-09",
        "requirements": "none",
        "category": "BMW MGU",
        "notes": "From hdshare/tm/dumm/<number>.gzip, gzip-compressed JSON documents that sit "
                 "among several thousand two-byte files holding 'OK' in the same folder. A "
                 "file is read only when it inflates to a JSON object with a position member. "
                 "Tested on one BMW MGU unit read from the logical zip of its persistence "
                 "volume, which held 150 such documents numbered from 31 to 8,096. What "
                 "component writes them and where they are sent is not established here; the "
                 "folder and key names are all there is to go on. Each document lists its data "
                 "privacy settings as a name and a one-letter value. Identical values are "
                 "folded: the 150 documents gave 51 rows for 37 setting names, 13 of which "
                 "appear with more than one value across the documents. The request number "
                 "does not give a reliable order, so the lowest and highest numbers bound "
                 "where a value was seen and do not date a change. The values seen were C, I "
                 "and U; what each letter stands for is not documented here and they are shown "
                 "as stored. A row records what the unit wrote about a setting. It does not "
                 "establish who changed it.",
        "paths": ('*/tm/dumm/*.gzip',),
        "sample_data": {
            "bmw_mgu_2024_pers_logical": "BMW MGU, logical zip | 51 rows",
        },
        "output_types": "standard",
        "artifact_icon": "shield",
    },
}

_NUMBER = re.compile(r'^(\d+)\.gzip$')


def _documents(context):
    """(request number, document, relative path, path, file modified time or '')."""
    seeker = context.get_seeker()
    infos = getattr(seeker, 'file_infos', {}) or {}
    found = []
    for file_found in set(str(f) for f in context.get_files_found()):
        named = _NUMBER.match(os.path.basename(file_found))
        if not named or os.path.isdir(file_found):
            continue
        relative = context.get_relative_path(file_found)
        try:
            with open(file_found, 'rb') as handle:
                document = json.loads(gzip.decompress(handle.read()).decode('utf-8'))
        except (OSError, ValueError, EOFError):
            logfunc(f'BMW MGU request documents: {relative} is not gzip-compressed JSON, '
                    'not read')
            continue
        if not isinstance(document, dict) or not isinstance(document.get('position'), dict):
            continue
        modified = getattr(infos.get(file_found), 'modification_date', None)
        stamp = ''
        if isinstance(modified, (int, float)) and modified > 0:
            stamp = datetime.fromtimestamp(modified, timezone.utc).strftime(
                '%Y-%m-%d %H:%M:%S')
        found.append((int(named.group(1)), document, relative, file_found, stamp))
    return sorted(found, key=lambda item: item[0])


def _text(value):
    return '' if value is None else value


@artifact_processor
def bmw_mgu_request_documents(context):
    data_list = []
    source_paths = []
    for number, document, relative, path, stamp in _documents(context):
        position = document['position']
        capabilities = document.get('vehicleCapabilities')
        if not isinstance(capabilities, dict):
            capabilities = {}
        source_paths.append(path)
        valid = position.get('valid')
        data_list.append((stamp, number,
                          _text(position.get('latitude')) if valid else '',
                          _text(position.get('longitude')) if valid else '',
                          _text(position.get('altitude')),
                          'true' if valid is True else 'false' if valid is False else '',
                          _text(document.get('requestReason')), _text(document.get('counter')),
                          _text(capabilities.get('mileageEnum')),
                          _text(capabilities.get('posAgeEnum')),
                          _text(capabilities.get('iStepCurrent')),
                          _text(capabilities.get('mguVersion')),
                          _text(document.get('requestIdentifier')), relative))

    data_headers = (('File Modified Time', 'datetime'), 'Request Number', 'Latitude',
                    'Longitude', 'Altitude (as stored)', 'Position Valid', 'Request Reason',
                    'Counter', 'Mileage Band (as stored)', 'Position Age Band (as stored)',
                    'Integration Level', 'MGU Version', 'Request Identifier', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)


@artifact_processor
def bmw_mgu_request_privacy_settings(context):
    folded = {}
    source_paths = []
    for number, document, _relative, path, _stamp in _documents(context):
        settings = document.get('dataPrivacySettings')
        if not isinstance(settings, dict):
            continue
        source_paths.append(path)
        for name, value in settings.items():
            folded.setdefault((str(name), str(_text(value))), []).append(number)

    data_list = [(name, value, len(numbers), min(numbers), max(numbers))
                 for (name, value), numbers in sorted(folded.items())]
    data_headers = ('Setting', 'Value (as stored)', 'Documents With This Value',
                    'Lowest Request Number', 'Highest Request Number')
    return data_headers, data_list, '\n'.join(source_paths)
