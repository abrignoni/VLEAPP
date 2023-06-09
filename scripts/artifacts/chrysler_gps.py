import csv
import os
import re
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']



## Get GPS data
def get_gpsdata(files_found, report_folder, seeker, wrap_text):
    data_list = []
    for file_found in files_found:
        try:
            with open(file_found, "r", encoding = "ISO-8859-1") as f:
                for line in f:
                    try:
                        line_str = str(line)
                        line_str_decoded = bytes(line_str, "utf-8").decode("unicode_escape", errors="replace")
                        line_decoded = re.sub('r\\\\x[0-9a-fA-F]{2}', "", line_str_decoded)
                        line_wanted = line_decoded.encode('ascii', 'ignore').decode('ascii', errors="replace") 
                        if line_wanted.contains("Latitude"):
                            data_list.append((line_wanted))
                    except UnicodeDecodeError:
                        pass
        except PermissionError:
            print("directory is not writable")

    if len(data_list) > 0:
        report = ArtifactHtmlReport('GPS Info')
        report.start_artifact_report(report_folder, f'GPS Info')
        report.add_script()
        data_headers = ('Latitude','Longitude', 'Timestamp')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'GPS Info'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No GPS Info Found')



        


__artifacts__ = {
       "gps_data": (
         "gps_data",
         ('*/log/slog*'),
         get_gpsdata)
}