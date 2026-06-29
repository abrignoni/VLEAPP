__artifacts_v2__ = {
    "chryslerContacts": {
        "name": "Chrysler - Contacts List",
        "description": "Voice-recognition phonebook contacts (name/information pairs) from a "
                       "Chrysler voice/asr phonebook export.",
        "author": "Joe Dinsmoor",
        "version": "0.2",
        "creation_date": "2023-06-05",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "Lines are read as alternating name / information pairs, as in the original.",
        "paths": ('*/voice/asr/context/phonebook/*.txt',),
        "output_types": "standard",
        "artifact_icon": "user",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def chryslerContacts(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            name = ''
            for count, line in enumerate(f):
                if count % 2 == 0:
                    name = line.strip()
                else:
                    data_list.append((name, line.strip()))

    data_headers = ('Name', 'Information')
    return data_headers, data_list, context.get_relative_path(source_path)
