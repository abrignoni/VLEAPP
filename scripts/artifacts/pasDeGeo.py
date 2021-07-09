import csv
import os
import scripts.artifacts.artGlobals 
import os
import re

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, kmlgen, timeline, is_platform_windows

#Compatability Data
vehicles = ['Ford Mustang','F-150']
platforms = ['SYNC3.2V2','SYNCGen3.0_3.0.18093_PRODUC T','SyncGen3_v2_b']

def timeorder(line):
    month = line.split('/', 3)[0]
    day = line.split('/', 3)[1]
    yeartime = line.split('/', 3)[2]
    year = yeartime.split(' ')[0]
    time = yeartime.split(' ')[1]
    timestamp = f'{year}-{month}-{day} {time}'
    return timestamp

def degtodec(deg, min, sec):
    deg = float(deg)
    if deg < 0:
        min = -abs(float(min))/60
        sec = -abs(float(sec))/3600
    else:
        min = float(min)/60
        sec = float(sec)/3600
    decimal = deg+min+sec
    return decimal

def get_pasDeGeo(files_found, report_folder, seeker, wrap_text):
    data_list_scan = []
    data_list_dev = []
    for file_found in files_found:
        basename = os.path.basename(file_found)
        with open(file_found, 'r', encoding='windows-1252') as f:
            for line in f:
                if 'NAV_FRAMEWORK_IF' in line: #put a print here to get all GPS stuff related to nav    
                    if 'dev_loc_results' in line:
                        if 'ERROR  RPT!!!' in line:
                            pass 
                        elif 'Longitude =' in line:
                            #print(line)
                            timestamp = timeorder(line)
                            devmatchObj1 = re.search(r"(Longitude =  ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj2 = re.search(r"(Latitude = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj7 = re.search(r"(Altitude = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj8 = re.search(r"(Heading = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            category = 'NAV_FRAMEWORK_IF'
                            subcategory = 'dev_loc_results'
                            #logfunc(line)
                            data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
                        elif 'Lon =' in line:
                            #print(line)
                            timestamp = timeorder(line)
                            devmatchObj1 = re.search(r"(Lon =  ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj2 = re.search(r"(Lat = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj7 = re.search(r"(Alt = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            devmatchObj8 = re.search(r"(Heading = ([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?)", line)
                            category = 'NAV_FRAMEWORK_IF'
                            subcategory = 'dev_loc_results'
                            logfunc(line)
                            data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
            
                            
    if len(data_list_dev) > 0:
        report = ArtifactHtmlReport('Dev Loc Results')
        report.start_artifact_report(report_folder, f'Dev Loc Results')
        report.add_script()
        data_headers_dev = ('Timestamp','Latitude','Longitude', 'Altitude Ft', 'Heading', 'Category', 'Subcategory', 'Log Filename')
        file_found = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_dev, data_list_dev, file_found)
        report.end_artifact_report()
        
        tsvname = f'Dev Loc Results'
        tsv(report_folder, data_headers_dev , data_list_dev, tsvname)
        
        tlactivity = 'Dev Loc Results'
        timeline(report_folder, tlactivity, data_list_dev, data_headers_dev)
        
        kmlactivity = 'Dev Loc Results'
        kmlgen(report_folder, kmlactivity, data_list_dev, data_headers_dev)
        
    else:
        logfunc(f'No Dev Loc Results available')