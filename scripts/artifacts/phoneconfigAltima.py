import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, kmlgen, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Nissan Altima',]
platforms = ['-',]

def get_phoneconfigAltima(files_found, report_folder, seeker, wrap_text, time_offset):
    
    for file_found in files_found:
        file_found = str(file_found)
        
        data_list = []
        start = None
        
        with open(file_found, 'r') as f:
            for line in f.readlines():
                if '[' in line:
                    start = line.replace('[','')
                    start = start.replace(']','')
                    start = start.replace('_',' ')
                    start = start.strip()
                    
                if '=' in line:
                    splitted = line.split('=')
                    key = splitted[0]
                    value = splitted[1]
                    if value == '\n':
                        continue
                    else:
                        data_list.append((key, value))
                        
                if line == '\n':
                    if start is None:
                        continue
                    else:
                        if len(data_list) > 0:
                            report = ArtifactHtmlReport(f'Phone Config {start}')
                            report.start_artifact_report(report_folder, f'Phone Config {start}')
                            report.add_script()
                            data_headers = ('Key','Value')
                            report.write_artifact_data_table(data_headers, data_list, file_found)
                            report.end_artifact_report()
                            
                            tsvname = f'Phone Config {start}'
                            tsv(report_folder, data_headers, data_list, tsvname)
                            
                        else:
                            logfunc(f'No Phone Config {start} data available')
                        
                        data_list = []


__artifacts__ = {
        "phoneConfig": (
                "Phone Config",
                ('*/ffs/phone_config.dat'),
                get_phoneconfigAltima)
}