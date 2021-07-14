import csv
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

def get_pasDeGeo(files_found, report_folder, seeker, wrap_text):
    data_list_dev = []
    data_list_speed = []
    data_list_apinfo = []
    data_list_vspeed = []
    data_list_transm = []
    data_list_outtemp = []
    for file_found in files_found:
        basename = os.path.basename(file_found)
        with open(file_found, 'r', encoding='cp437') as f:
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
                            #logfunc(line)
                            data_list_dev.append((timestamp, devmatchObj2[2], devmatchObj1[2], devmatchObj7[2], devmatchObj8[2], category, subcategory, basename))
                
                if 'Speed limit' in line:
                    timestamp = timeorder(line)
                    lineparts = line.split(',')
                    streetname = lineparts[-2].split(':')[-1].replace('[', '').replace(']', '').strip()
                    speedlimit = int(lineparts[-1].split(':')[-1].replace('[', '').replace(']', '').strip())
                    if streetname:
                        data_list_speed.append((timestamp, streetname, speedlimit, basename))
                        
                if 'WIFI_MID' in line:
                    if 'Extracted BSSID' in line:
                        timestamp = timeorder(line)
                        lineparts = line.split('=')
                        extractedbssid = lineparts[-1].strip()
                    if 'SSID:' in line:
                        lineparts = line.split(';')
                        ssid = lineparts[0].split(':')[-1].strip()
                        signalstrenght = lineparts[-1].split(',')[-1].split(':')[-1].strip()
                        data_list_apinfo.append((timestamp, extractedbssid, ssid, signalstrenght, basename))
                
                if 'QT_HMI'	in  line:
                    if 'VehicleSpeed' in line:
                        timestamp = timeorder(line)
                        lineparts = line.strip().split(' ')
                        data_list_vspeed.append((timestamp, lineparts[-1].replace('"',''), basename))
                
                    if 'TransmissionStatus' in line: 
                        timestamp = timeorder(line)
                        lineparts = line.strip().split(' ')
                        data_list_transm.append((timestamp, lineparts[-1].replace('"','').strip(), basename))
                    
                    if 'General_Temperature_Unit_INT' in line:
                        timestamp = timeorder(line)
                        lineparts = line.strip().split(' ')
                        data_list_outtemp.append((timestamp,'Temp. Unit: '+ lineparts[-1].replace('"','').strip(), basename))
                        
                    if 'OutsideAirTemperature_E_FLT' in line:
                        timestamp = timeorder(line)
                        lineparts = line.strip().split(' ')
                        data_list_outtemp.append((timestamp, lineparts[-1].replace('"','').strip(), basename ))
                        
    if len(data_list_dev) > 0:
        report = ArtifactHtmlReport('Dev Loc Results')
        report.start_artifact_report(report_folder, f'Dev Loc Results')
        report.add_script()
        data_headers_dev = ('Timestamp','Latitude','Longitude', 'Altitude Ft', 'Heading', 'Category', 'Subcategory', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_dev, data_list_dev, pathname)
        report.end_artifact_report()
        
        tsvname = f'Dev Loc Results'
        tsv(report_folder, data_headers_dev , data_list_dev, tsvname)
        
        tlactivity = 'Dev Loc Results'
        timeline(report_folder, tlactivity, data_list_dev, data_headers_dev)
        
        kmlactivity = 'Dev Loc Results'
        kmlgen(report_folder, kmlactivity, data_list_dev, data_headers_dev)
        
    else:
        logfunc(f'No Dev Loc Results available')
        
    if len(data_list_speed) > 0:
        report = ArtifactHtmlReport('Road Speed Limits')
        report.start_artifact_report(report_folder, f'Road Speed Limits')
        report.add_script()
        data_headers_speed = ('Timestamp','Road','Speed Limit', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_speed, data_list_speed, pathname)
        report.end_artifact_report()
        
        tsvname = f'Road Speed Limits'
        tsv(report_folder, data_headers_speed , data_list_speed, tsvname)
        
        tlactivity = 'Road Speed Limits'
        timeline(report_folder, tlactivity, data_list_speed, data_headers_speed)
        
    else:
        logfunc(f'No Road Speed Limits available')
    
    if len(data_list_apinfo) > 0:
        report = ArtifactHtmlReport('Access Point List')
        report.start_artifact_report(report_folder, f'Access Point List')
        report.add_script()
        data_headers_apinfo = ('Timestamp','BSSID','SSID', 'Signal Strength', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_apinfo, data_list_apinfo, pathname)
        report.end_artifact_report()
        
        tsvname = f'Access Point List'
        tsv(report_folder, data_headers_apinfo , data_list_apinfo, tsvname)
        
        tlactivity = 'Access Point List'
        timeline(report_folder, tlactivity, data_list_apinfo, data_headers_apinfo)
        
    else:
        logfunc(f'No Access Point List available')
    
    if len(data_list_vspeed) > 0:
        report = ArtifactHtmlReport('Vehicle Speed')
        report.start_artifact_report(report_folder, f'Vehicle Speed')
        report.add_script()
        data_headers_vspeed = ('Timestamp','Vehicle Speed','Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_vspeed, data_list_vspeed, pathname)
        report.end_artifact_report()
        
        tsvname = f'Vehicle Speed'
        tsv(report_folder, data_headers_vspeed , data_list_vspeed, tsvname)
        
        tlactivity = 'Vehicle Speed'
        timeline(report_folder, tlactivity, data_list_vspeed, data_headers_vspeed)
    else:
        logfunc(f'No Vehicle Speed available')
    
    if len(data_list_transm) > 0:
        report = ArtifactHtmlReport('Transmission Status')
        report.start_artifact_report(report_folder, f'Transmission Status')
        report.add_script()
        data_headers_transm = ('Timestamp','Transmission Status','Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_transm, data_list_transm, pathname)
        report.end_artifact_report()
        
        tsvname = f'Transmission Status'
        tsv(report_folder, data_headers_transm , data_list_transm, tsvname)
        
        tlactivity = 'Transmission Status'
        timeline(report_folder, tlactivity, data_list_transm, data_headers_transm)
        
    else:
        logfunc(f'No Transmission Status available')
        
    if len(data_list_outtemp) > 0:
        report = ArtifactHtmlReport('Outside Temperature')
        report.start_artifact_report(report_folder, f'Outside Temperature')
        report.add_script()
        data_headers_outtemp = ('Timestamp','Temperature', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_outtemp, data_list_outtemp, pathname)
        report.end_artifact_report()
        
        tsvname = f'Outside Temperature'
        tsv(report_folder, data_headers_outtemp , data_list_outtemp, tsvname)
        
        tlactivity = 'Outside Temperature'
        timeline(report_folder, tlactivity, data_list_outtemp, data_headers_outtemp)
        
    else:
        logfunc(f'No Outside Temperature available')
        