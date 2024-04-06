import csv
import os
import re
import tarfile
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

def get_pasDeGeoTarGz(files_found, report_folder, seeker, wrap_text, time_offset):
    vinlist = []
    platformversion = []
    data_list_dev = []
    data_list_speed = []
    data_list_apinfo = []
    data_list_vspeed = []
    data_list_transm = []
    data_list_outtemp = []
    data_list_odometer = []
    data_list_curroad = []
    
    for file_found in files_found:
        #logfunc(' ')
        #logfunc(file_found)
        if file_found.endswith('.tar.gz'):
            size = os.stat(file_found).st_size
            if size > 0:
                with tarfile.open(file_found, 'r') as tar:
                    try:
                        tar.extract('pas_debug.log.1', report_folder)
                    except KeyError:
                        logfunc(f"Warning: File 'pas_debug.log.1' not found in {file_found}.")
                    else:
                        source = Path(report_folder, 'pas_debug.log.1')
                        basename = os.path.basename(file_found)
                        #logfunc(basename)
                        
                        with open(source, 'r', encoding='cp437') as f:
                            for line in f:
                                
                                #Done
                                if ': lat: '  and 'lon:' in line:
                                    timestamp = timeorder(line)
                                    lineparts = line.split(': lat: ')[1]
                                    linepartsplit = lineparts.split(',')
                                    latitude = linepartsplit[0]
                                    longitude = linepartsplit[1].split('lon: ')[1]
                                    heading = linepartsplit[2].split('heading: ')[1]
                                    data_list_dev.append((timestamp, latitude, longitude, heading, basename))
                    
                                #Done
                                if 'ICDisplayDataFromNaviCoreDebugLog' and '= Speed Limit:' in line:
                                    if 'Speed limit invalid' in line:
                                        pass
                                    else:
                                        timestamp = timeorder(line)
                                        lineparts = line.split('=')
                                        streetname = ''
                                        speedlimit = lineparts[1]
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
                                
                                if 'nv_navigation/main/CI->SI'  and '] currentRoad' in line:
                                    try:
                                        timestamp = timeorder(line)
                                        currentroad = line.split('panaAPI notice -                               ] [')[1].split('] currentRoad')[0]
                                        data_list_curroad.append((timestamp, currentroad, basename))
                                    except:
                                        logfunc(f'Error on current road: {line}')
                                
                                #Done
                                if '[SAL_SWITCH_DISPLAY] Received speed:' in line:
                                    timestamp = ''
                                    try:
                                        timestamp = timeorder(line)
                                    except: 
                                        logfunc(f'Error in {line}')
                                    lineparts = line.split('[SAL_SWITCH_DISPLAY] Received speed:')
                                    speeds = lineparts[1].strip()
                                    speeds = speeds.split(' kmph')[0]
                                    data_list_vspeed.append((timestamp, speeds))
                                    #except: 
                                        #logfunc(f'Error in {line}')
                                    
                                
                                if 'QT_HMI'	in  line:
                                    
                                
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
                                
                                if 'USBUPDT_MID' in line:
                                    if '=Line read is Version Number =' in line:
                                        lineparts = line.strip().split('=')
                                        ver = lineparts[-1].strip()
                                        if ver not in platformversion:
                                            platformversion.append(ver)
                                            
                                
                                if 'CAppLinkService' in line:
                                    timestampLink = timeorder(line)
                                    
                                if 'odometer' in line: 
                                    lineparts = line.strip().split(':')
                                    data_list_odometer.append((timestampLink, lineparts[-1].strip(), basename))
                                
                                if '"vin":' in line:
                                    vind = (line.split('vin')[1].split(',')[0])
                                    vin = (vind.split('"')[2])
                                    if vin not in vinlist:
                                        vinlist.append(vin)
                                        
                                if 'VIN got from GGC' in line:
                                    lineparts = line.strip().split('=')
                                    vin = lineparts[-1].strip()
                                    if vin not in vinlist:
                                        vinlist.append(vin)
                                
                                if '"make"' in line:
                                    linepartsma = line.strip().split(':')
                                    make = linepartsma[-1].strip().replace('"','')
                                
                                if 'Model_Id::' in line:
                                    model = (line.split('Model_Id::')[1].split(' ')[0])
                                    number = (line.split('Model_Id::')[1].split(' ')[1])
                                    model = f'{model} {number}'
                                
                                if '=Vehicle Model Year = ' in line:
                                    yearc = line.split('=Vehicle Model Year = ')[1]
    
                                    
    try:
        if yearc:
            logdevinfo(f'Model Year from pas_debug in tar.gz: {yearc}')
    except:
        pass
    
    try:
        if make:
            logdevinfo(f'Make from pas_debug: {make}')
    except:
        pass
    
    try:
        if model:
            logdevinfo(f'Model from pas_debug in tar.gz: {model}')
    except:
        pass
        
    if len(vinlist) > 0:
        for item in vinlist:
            logdevinfo(f"VIN from pas_debug in tar.gz: {item}")
    
    if len(platformversion) > 0:
        for item in platformversion:
            logdevinfo(f"Platform from pas_debug: {item}")
    
    if len(data_list_dev) > 0:
        report = ArtifactHtmlReport('GPS Locations')
        report.start_artifact_report(report_folder, f'GPS Locations')
        report.add_script()
        data_headers_dev = ('Timestamp','Latitude','Longitude', 'Heading', 'Log Filename')
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
        data_headers_vspeed = ('Timestamp','Vehicle Speed KMPH')
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
        
    if len(data_list_odometer) > 0:
        report = ArtifactHtmlReport('Odometer')
        report.start_artifact_report(report_folder, f'Odometer')
        report.add_script()
        data_headers_odometer = ('Timestamp','Odometer','Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_odometer, data_list_odometer, pathname)
        report.end_artifact_report()
        
        tsvname = f'Odometer'
        tsv(report_folder, data_headers_odometer , data_list_odometer, tsvname)
        
        tlactivity = 'Odometer'
        timeline(report_folder, tlactivity, data_list_odometer, data_headers_odometer)
        
    else:
        logfunc(f'No Odometer available')
        
    if len(data_list_dev) > 0:
        report = ArtifactHtmlReport('Current Road')
        report.start_artifact_report(report_folder, f'Current Road')
        report.add_script()
        data_headers_curroad = ('Timestamp','Current Road', 'Log Filename')
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_curroad, data_list_curroad, pathname)
        report.end_artifact_report()
        
        tsvname = f'Current Road'
        tsv(report_folder, data_headers_dev , data_list_dev, tsvname)
        
        tlactivity = 'Current Road'
        timeline(report_folder, tlactivity, data_list_dev, data_headers_dev)
    else:
        logfunc(f'No Current Road data available')
        
__artifacts__ = {
        "pas_DebugTarGZ": (
                "pas_DebugTarGZ",
                ('*/archivedata/*.tar.gz'),
                get_pasDeGeoTarGz)
}