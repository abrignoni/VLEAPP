__artifacts_v2__ = {
    "VW_MIB2_Core_Info": {
        "name": "Core Info",
        "description": "Retrieve core-related data from Volkswagen Vehicles",
        "author": "@posiwer",
        "version": "0.8",
        "date": "2025-01-07",
        "requirements": "none",
        "category": "Volkswagen Vehicle",
        "notes": "",
        "paths": ('*/startup-*/*SESSION-*', ),
        "function": "get_Core_Information"
    }
}

import os
import gzip
import shutil
import json
import re
from datetime import datetime
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import tsv, logfunc

def extract_gz_sessions(files_found, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    extracted_files = []
    for file in files_found:
        filename = os.path.basename(file)
        parent_folder = os.path.basename(os.path.dirname(file))

        if filename.startswith("SESSION-") and filename.endswith(".gz"):
            expected_uncompressed = filename[:-3]
            sibling_uncompressed = os.path.join(os.path.dirname(file), expected_uncompressed)

            if os.path.exists(sibling_uncompressed):
                logfunc(f"[INFO] Skipping {filename} (uncompressed version exists)")
                continue

            output_filename = f"{parent_folder}_{expected_uncompressed}"
            output_path = os.path.join(output_folder, output_filename)

            try:
                with gzip.open(file, 'rb') as f_in, open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

                extracted_files.append(output_path)
            except Exception as e:
                logfunc(f"[ERROR] Failed to extract {filename}: {str(e)}")
    return extracted_files

def copy_existing_sessions(files_found, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    copied_files = []
    for file in files_found:
        filename = os.path.basename(file)
        parent_folder = os.path.basename(os.path.dirname(file))
        if filename.startswith("SESSION-") and not filename.endswith(".gz"):
            output_filename = f"{parent_folder}_{filename}"
            output_path = os.path.join(output_folder, output_filename)

            try:
                shutil.copy(file, output_path)
                copied_files.append(output_path)
            except Exception as e:
                logfunc(f"[ERROR] Failed to copy {filename}: {str(e)}")
    return copied_files

def parse_vcard_fields(vcard):
    name = number = call_type = date = ''
    lines = vcard.splitlines()

    for line in lines:
        if line.startswith('FN:') or line.startswith('N:'):
            name = line.split(':', 1)[1].strip()
        elif line.startswith('TEL'):
            number = line.split(':', 1)[1].strip()
        elif 'X-IRMC-CALL-DATETIME' in line:
            parts = line.split(':')
            if len(parts) == 2:
                raw_dt = parts[1].strip()
                meta = parts[0]
                if 'TYPE=' in meta:
                    call_type = meta.split('TYPE=')[-1].strip().capitalize()
                else:
                    call_type = 'Unknown'
                try:
                    dt = datetime.strptime(raw_dt, "%Y%m%dT%H%M%S")
                    date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    date = raw_dt

    if all([name, number, call_type, date]):
        return (date, number, name, call_type)
    return None

def extract_connected_device(line):
    if "serviceState=" in line and "Connected" in line and "bdAddr=" in line and "name=" in line:
        mac_match = re.search(r'bdAddr=\s*0x([0-9a-fA-F]+)', line)
        name_match = re.search(r"name=\s*'([^']+)'", line)
        if mac_match and name_match:
            mac_raw = mac_match.group(1)
            mac = ':'.join(mac_raw[i:i+2] for i in range(0, len(mac_raw), 2)).upper()
            name = name_match.group(1).strip()
            return name, mac
    return None

def get_Core_Information(files_found, report_folder, seeker, wrap_text, time_offset):
    extraction_folder = os.path.join(report_folder, "Extracted Sessions")
    extracted = extract_gz_sessions(files_found, extraction_folder)
    copied = copy_existing_sessions(files_found, extraction_folder)
    session_files = extracted + copied

    records = []

    for sf in session_files:
        source_file = os.path.basename(sf)
        try:
            with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            current_device = ("Unknown", "Unknown")

            for idx, line in enumerate(lines):
                if "serviceState=" in line and "Connected" in line:
                    device_info = extract_connected_device(line)
                    if device_info:
                        current_device = device_info

                if 'BT_APPL_PIM_DATA_IND' in line and 'BEGIN:VCARD' in line:
                    start = line.find('BEGIN:VCARD')
                    end = line.find('END:VCARD') + len('END:VCARD')
                    if start != -1 and end != -1:
                        vcard_raw = line[start:end].replace('..', '\n').strip()
                        parsed = parse_vcard_fields(vcard_raw)
                        if parsed:
                            date, number, name, call_type = parsed
                            records.append((
                                source_file, date, number, name, call_type,
                                current_device[0], current_device[1]
                            ))
        except Exception as e:
            logfunc(f"[ERROR] Failed to process {source_file}: {str(e)}")
            continue

    if records:
        headers = ['Source File', 'Date', 'Phone Number', 'Contact Name', 'Call Type', 'Device Name', 'Device MAC']
        report = ArtifactHtmlReport('Bluetooth Call Logs')
        report.start_artifact_report(report_folder, 'Bluetooth Call Logs')
        report.add_script()
        report.write_artifact_data_table(headers, records, 'core/startup-*/SESSION-*')
        report.end_artifact_report()

        tsv(report_folder, headers, records, 'Bluetooth Call Logs')

        with open(os.path.join(report_folder, 'bluetooth_calls.json'), 'w', encoding='utf-8') as f:
            json.dump([dict(zip(headers, r)) for r in records], f, indent=4, ensure_ascii=False)
