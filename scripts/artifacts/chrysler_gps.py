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
        with open(file_found, "r") as f:
            while(data_list == ''):
                try:
                    for line in f:
                        line_str = str(line)
                        line_str_decoded = bytes(line_str, "utf-8").decode("unicode_escape", errors="replace")
                        line_decoded = re.sub('r\\\\x[0-9a-fA-F]{2}', "", line_str_decoded)
                        line_wanted = line_decoded.encode('ascii', 'ignore').decode('ascii', errors="replace") 
                        devmatchObj1 = re.search(r"(Latitude\sread\s from\sPS:\s\d\d\.\d\d\d\d\d\d\sLongitude\sread\sfrom\sPS:\s-\d\d\.\d\d\d\d\d\d\d)", line_wanted)
                        data_list.append((devmatchObj1))
                except UnicodeDecodeError:
                    pass
    if len(data_list) > 0:
        report = ArtifactHtmlReport('GPS Info')
        report.start_artifact_report(report_folder, f'GPS Info')
        report.add_script()
        data_headers = ('Key','Value')
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'GPS Info'
        tsv(report_folder, data_headers, data_list, tsvname)
    else:
        logfunc(f'No GPS Info Found')



        


__artifacts__ = {
       "gps_data": (
         "gps_data",
         ('*/mnt/p3/log/slogs*'),
         get_gpsdata)
}