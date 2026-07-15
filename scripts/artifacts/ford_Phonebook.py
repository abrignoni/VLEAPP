__artifacts_v2__ = {
    "get_PhoneBook": {
        "name": "Phonebook Contacts",
        "description": "Phonebook contacts (name + number list) from Ford vehicles (BTPhonebook).",
        "author": "@JaysonU25",
        "version": "0.2",
        "creation_date": "2024-11-20",
        "last_update_date": "2026-06-29",
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "Phone Number(s) is a comma-joined list, so it is left as text (not tagged "
                 "phonenumber).",
        "paths": ('*/BTPhonebook*',),
        "output_types": "standard",
        "artifact_icon": "phone",
    }
}

from scripts.ilapfuncs import artifact_processor


def format_number(number):
    formatted_number = ""
    for num in number:
        if num.isdigit():
            formatted_number = formatted_number + num
    if len(formatted_number) <= 10:
        formatted_number = f"{formatted_number[0:3]}-{formatted_number[3:6]}-{formatted_number[6:]}"
    elif len(formatted_number) >= 11:
        formatted_number = (f"+{formatted_number[0]}-{formatted_number[1:4]}-"
                            f"{formatted_number[4:7]}-{formatted_number[7:]}")
    return formatted_number


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
                name = phone_number = ''
                found_num = False
                lineparts = line.split("ADDRESS")[0].split("\t")
                for entry in lineparts:
                    if entry == '':
                        continue
                    if found_num:
                        if entry[-1].isnumeric() and len(entry) >= 10:
                            new_number = format_number(entry)
                            if new_number not in phone_number:
                                phone_number = phone_number + new_number + ", "
                    elif entry in ("address", "insert") or entry.isnumeric():
                        continue
                    elif entry == "NUMBERS":
                        found_num = True
                    else:
                        name += entry + " "
                name = name.strip()
                phone_number = phone_number.strip()[0:-1]
                if name and phone_number and (name, phone_number) not in data_list:
                    data_list.append((name, phone_number))

    data_headers = ('Name', 'Phone Number(s)')
    return data_headers, data_list, context.get_relative_path(source_path)
