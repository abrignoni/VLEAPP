__artifacts_v2__ = {
    "get_PhoneBook": {
        "name": "Ford - Phonebook Contacts",
        "description": "Phonebook contacts (name + number list) from Ford vehicles (BTPhonebook).",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-10-04",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Phone Number(s) is a comma-joined list of the tab-separated entries "
                 "that follow NUMBERS on an address insert line, each shown as the file "
                 "holds it. Only entries of 10 or more characters that end in a digit are "
                 "listed. An entry repeated character for character on the same line is "
                 "listed once, and a contact with no listed number is not reported. This "
                 "behaviour was checked on a constructed file; no registered corpus holds "
                 "a BTPhonebook file.",
        "paths": ('*/BTPhonebook*',),
        "output_types": "standard",
        "artifact_icon": "phone",
    }
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def get_PhoneBook(context):
    data_list = []
    source_path = ''
    for file_found in context.get_files_found():
        file_found = str(file_found)
        source_path = file_found
        with open(file_found, encoding='utf-8', errors='backslashreplace') as f:
            for line in f:
                if "address\tinsert" not in line:
                    continue
                name = ''
                numbers = []
                found_num = False
                lineparts = line.split("ADDRESS")[0].split("\t")
                for entry in lineparts:
                    if entry == '':
                        continue
                    if found_num:
                        if entry[-1].isnumeric() and len(entry) >= 10:
                            new_number = entry
                            if new_number not in numbers:
                                numbers.append(new_number)
                    elif entry in ("address", "insert") or entry.isnumeric():
                        continue
                    elif entry == "NUMBERS":
                        found_num = True
                    else:
                        name += entry + " "
                name = name.strip()
                phone_number = ', '.join(numbers)
                if name and phone_number and (name, phone_number) not in data_list:
                    data_list.append((name, phone_number))

    data_headers = ('Name', 'Phone Number(s)')
    return data_headers, data_list, context.get_relative_path(source_path)
