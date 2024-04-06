import csv
import os
import re
import tarfile
import datetime
from pathlib import Path

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, kmlgen, timeline, is_platform_windows

#Compatability Data
vehicles = ['RAM 1500']
platforms = []
 
def timeorder(line):
    month = line.split('/', 3)[0]
    day = line.split('/', 3)[1]
    yeartime = line.split('/', 3)[2]
    year = yeartime.split(' ')[0]
    time = yeartime.split(' ')[1]
    timestamp = f'{year}-{month}-{day} {time}'
    return timestamp

def get_logparser(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    
    for file_found in files_found:
        #logfunc(' ')
        #logfunc(file_found)
        basename = os.path.basename(file_found)
        with open(file_found, 'r', encoding='cp437') as f:
            for line in f:
                if '[INFO] LocationDistributor[KONA-LIB] Location details: ' in line:
                    linesplit = line.split('[INFO] LocationDistributor[KONA-LIB] Location details: ')[1]
                    linesplit = linesplit.split(';')
                    latitude = linesplit[1].split(' ')[2]
                    longitude = linesplit[2].split(' ')[2]
                    altitude = linesplit[4].split(' ')[2]
                    horzac = linesplit[5].split(' ')[3]
                    vertac = linesplit[6].split(' ')[3]
                    times = linesplit[7].split(' ')[3]
                    times = int(times)
                    times = datetime.datetime.utcfromtimestamp(times).strftime('%Y-%m-%d %H:%M:%S')
                    course = linesplit[8].split(' ')[2]
                    speed = linesplit[9].split(' ')[2]
                    azimuth = linesplit[10].split(' ')[2]
                    locm = linesplit[11].split(' ')[3]
                    
                    data_list.append((times, latitude, longitude, horzac, vertac, altitude, course, speed, azimuth, basename))
                    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('GPS Locations from Logs')
        report.start_artifact_report(report_folder, f'GPS Locations from Logs')
        report.add_script()
        data_headers_dev = ('Timestamp','Latitude','Longitude', 'Horizontal Accuracy', 'Vertical Accuracy', 'Altitude', 'Course', 'Speed', 'Azimuth', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_dev, data_list, pathname)
        report.end_artifact_report()
        
        tsvname = f'GPS Locations from Logs'
        tsv(report_folder, data_headers_dev , data_list, tsvname)
        
        tlactivity = 'GPS Locations from Logs'
        timeline(report_folder, tlactivity, data_list, data_headers_dev)
        
        kmlactivity = 'GPS Locations from Logs'
        kmlgen(report_folder, kmlactivity, data_list, data_headers_dev)
        
    else:
        logfunc(f'No GPS Locations from Logs results available')
        
    
        
__artifacts__ = {
        "logparser": (
                "logparser",
                ('*/persistentLogs/*/Log*'),
                get_logparser)
}