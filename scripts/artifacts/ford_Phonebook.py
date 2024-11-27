__artifacts_v2__ = {
    "Phonebook_contacts": {
        "name": "Phonebook Contacts",
        "description": "Scrape the Phonebook from Ford Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-10-30",  # Date of the latest version
        "requirements": "none",
        "category": "Ford Vehicles",
        "notes": "",
        "paths": ('*/BTPhonebook*'),
        "function": "get_PhoneBook"
    }
}

import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford','F-150']
platforms = ['']
    
def format_number(number: str) -> str:
    formatted_number = ""
    count = 0
    country_flag = False

    for num in number:
        if num.isdigit():
            formatted_number = formatted_number + num
            count += 1

    if len(formatted_number) <= 10:
        formatted_number = f"{formatted_number[0:3]}-{formatted_number[3:6]}-{formatted_number[6:]}"
    elif len(formatted_number) >= 11:
        formatted_number = f"+{formatted_number[0]}-{formatted_number[1:4]}-{formatted_number[4:7]}-{formatted_number[7:]}"
    return formatted_number
    

## Get connected Bluetooth Devices
def get_PhoneBook(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            for line in f:  # Search line for certain keywords
                found_num = False
                if line == "":
                    continue
                splits1 = ''
                if "address	insert" in line:
                    name = phone_number = '' # Initialize Variables
                    splits1 = line.split("ADDRESS")[0]
                    lineparts = splits1.split("\t")
                    for entry in lineparts:
                        if entry != '':
                            if found_num:
                                if entry[-1].isnumeric() and len(entry) >= 10:
                                    new_number = format_number(entry)
                                    if new_number not in phone_number:
                                        phone_number = phone_number + new_number + ", "
                                else:
                                    continue
                            else:
                                if entry == "address" or entry == "insert" or entry.isnumeric():
                                    continue
                                elif entry == "NUMBERS":
                                    found_num = True
                                else:
                                    name += entry + " "
                        else:
                            continue
                    
                    name = name.strip()
                    phone_number = phone_number.strip()[0:-1]
                # Add found item to data list                
                if (name, phone_number) not in data_list and name != '' and phone_number != "":
                    data_list.append((name, phone_number)) # Add new found data to datalist
    
    if len(data_list) > 0: # Check to see if Data Found
        report = ArtifactHtmlReport('Phonebook Contacts')
        report.start_artifact_report(report_folder, f'Phonebook Contacts')
        report.add_script()
        data_headers = ("Name", "Phone Number(s)")
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        tsvname = f'Phonebook Contacts'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No Phonebook Contacts found')
