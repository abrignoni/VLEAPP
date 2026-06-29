__artifacts_v2__ = {
    "chryslerDiagnostics": {
        "name": "Chrysler - Diagnostic Data",
        "description": "Diagnostic key/value data from a Chrysler persistence/nonvol_*.ps log.",
        "author": "Joe Dinsmoor",
        "version": "0.2",
        "creation_date": "2023-06-02",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "Lines are read as alternating key / value pairs, as in the original.",
        "paths": ('*/persistence/nonvol_*.ps',),
        "output_types": "standard",
        "artifact_icon": "activity",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def chryslerDiagnostics(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            key = ''
            for count, line in enumerate(f):
                if count % 2 == 0:
                    key = line.strip()
                else:
                    data_list.append((key, line.strip()))

    data_headers = ('Key', 'Value')
    return data_headers, data_list, context.get_relative_path(source_path)
