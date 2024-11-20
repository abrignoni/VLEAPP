__artifacts_v2__ = {
    "Tar_GZ_Checker": {
        "name": "Tar GZ Checker",
        "description": "Scrape variety of data found in Tar.Gz files in Chrysler Vehicles",
        "author": "@JaysonU25",  # Replace with the actual author's username or name
        "version": "0.1",  # Version number
        "date": "2024-10-30",  # Date of the latest version
        "requirements": "none",
        "category": "Chrysler Vehicles",
        "notes": "",
        "paths": ('*/[H-M]_*.tar.gz'),
        "function": "get_TarGz"
    }
}


import csv
import os
import re
import tarfile
from pathlib import Path

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, kmlgen, timeline, is_platform_windows

#Compatability Data
vehicles = ['FCA', 'Jeep Grand Cherokee', 'Dodge Challenger 2019']
platforms = []
 
def timeorder(line):
    month = line.split('/', 3)[0]
    day = line.split('/', 3)[1]
    yeartime = line.split('/', 3)[2]
    year = yeartime.split(' ')[0]
    time = yeartime.split(' ')[1]
    timestamp = f'{year}-{month}-{day} {time}'
    return timestamp

def get_TarGz(files_found, report_folder, seeker, wrap_text, time_offset):
    vinlist = []
    timestamp_loc = ""
    timestamp = ""
    platformversion = []
    data_list_dev = []
    data_list_speed = []
    data_list_apinfo = []
    data_list_vspeed = []
    data_list_transm = []
    data_list_outtemp = []
    data_list_odometer = []
    data_list_curroad = []
    data_list_brake_status = []
    data_list_engine_temp = []
    data_list_interior_temp =[]
    data_list_tp = []
    data_list_gear_state = []
    data_list_door_status = []
    
    for file_found in files_found:
        if file_found.endswith('.tar.gz'):
            size = os.stat(file_found).st_size
            if size > 0:
                with tarfile.open(file_found, 'r') as tar:
                    file_name_1 = 'pas_debug.log.1'
                    file_name_2 = 'pas_debug.log'
                    file_name_found = ""
                    try:
                        tar.extract(file_name_1, report_folder)
                        file_name_found = file_name_1
                    except KeyError:
                        logfunc(f"Warning: File {file_name_1} not found in {file_found}.")
                        try:
                            tar.extract(file_name_2, report_folder)
                            file_name_found = file_name_2
                        except KeyError:
                            logfunc(f"Warning: File {file_name_2} not found in {file_found}.")
                    if(file_name_found != ""):
                        source = Path(report_folder, file_name_found)
                        basename = os.path.basename(file_found)
                        
                        with open(source, 'r', encoding='cp437') as f:
                            lat_flag = ': lat: '
                            lon_flag = 'lon:'
                            head_flag = 'heading: '
                            for line in f:
                                
                                if lat_flag  and lon_flag and head_flag in line:
                                    try:
                                        timestamp = timeorder(line)
                                    except: 
                                        logfunc(f'Error in {line}')
                                    if len(line.split(str(lat_flag))) > 1: # Random Error where this line gets reached but does not split
                                        lineparts = line.split(str(lat_flag))[1]
                                        linepartsplit = lineparts.split(',')
                                        latitude = linepartsplit[0]
                                        longitude = linepartsplit[1].split(lon_flag)[1]
                                        heading = linepartsplit[2].split(head_flag)[1]
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

                                if "Received Lat" in line:
                                    timestamp_loc = timeorder(line)
                                    lineparts = line.split("Received Lat ")[1].split(" ")
                                    latitude = lineparts[0]
                                    longitude = lineparts[2]

                                if 'eBrakePedalStatus: ' in line:
                                    timestamp = ''
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if len(line.split('eBrakePedalStatus: ')) > 1:
                                            lineparts = line.split('eBrakePedalStatus: ')[1].strip()
                                            brake_status = "Brake Pedal Pressed" if lineparts == "1" else ("Brake Pedal Released" if lineparts == "0" else "")
                                            data_found = (timestamp, brake_status, latitude, longitude)
                                            if data_found not in data_list_brake_status and timestamp != "" and brake_status != "":
                                                data_list_brake_status.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done
                                
                                if 'GENERAL_ENGINE_COOLANT_TEMPERATURE_EVENTHandler' in line:
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if len(line.split('=iTemp C: ')) > 1:
                                            engine_temp = line.split('=iTemp C: ')[1].strip()[0:2]
                                            data_found = (timestamp, engine_temp, latitude, longitude)
                                            if data_found not in data_list_engine_temp and timestamp != "" and engine_temp != "":
                                                data_list_engine_temp.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done

                                if 'GENERAL_VEHICLE_INTERIOR_TEMPERATURE_EVENTHandler' in line:
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if len(line.split('after scaling: ')) > 1:
                                            interior_temp = line.split('after scaling: ')[1].strip()
                                            data_found = (timestamp, interior_temp, latitude, longitude)
                                            if data_found not in data_list_interior_temp and timestamp != "" and interior_temp != "":
                                                data_list_interior_temp.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done
                                    
                                if 'TPM_A2_Callback' in line:
                                    pressure_read = ""
                                    tire = ""
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if len(line.split('=Published TIRE_PRESSURE')) > 1:
                                            if 'REAR_LEFT' in line:
                                                tire = "Rear Left Tire"
                                                pressure_read = line.strip().split(" ")[-1]
                                            elif 'REAR_REAR' in line:
                                                tire = "Rear Right Tire"
                                                pressure_read = line.strip().split(" ")[-1]
                                            elif 'FRONT_LEFT' in line:
                                                tire = "Front Left Tire"
                                                pressure_read = line.strip().split(" ")[-1]
                                            elif 'FRONT_REAR' in line:
                                                tire = "Front Right Tire"
                                                pressure_read = line.strip().split(" ")[-1]
                                            else:
                                                pressure_read = ''
                                            
                                            data_found = (timestamp, tire, pressure_read, latitude, longitude)
                                            if data_found not in data_list_tp and timestamp != "" and pressure_read != "":
                                                data_list_tp.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done
                                    
                                if "eGearState = " in line:
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if len(line.split('eGearState = ')) > 1:
                                            lineparts = line.split('eGearState = ')[1].strip()
                                            gear_state = "Gear is in Park" if lineparts == "1" else ("Gear is in Neutral" if lineparts == "2" else ("Gear is in Drive" if lineparts == "3" else ("Gear is in Reverse" if lineparts == "4" else "")))
                                            data_found = (timestamp, gear_state, latitude, longitude)
                                            if data_found not in data_list_gear_state and timestamp != "" and gear_state != "":
                                                data_list_gear_state.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done

                                if "_AJAR_" in line and "error" not in line and "Error" not in line:
                                    door_status = ""
                                    try:
                                        timestamp = timeorder(line)
                                        if timestamp[0:-3] != timestamp_loc[0:-3]:
                                            latitude = ""
                                            longitude = ""
                                        if "TRUNK_LIFT_GATE" in line: # Trunk event
                                            lineparts = line.split(' ')[-1].strip()
                                            if lineparts == '0':
                                                door_status = "Trunk Lift Gate Closed"
                                            elif lineparts == '1': 
                                                door_status = "Trunk Lift Gate Open"
                                        elif "DRIVE" in line: # Driver door event
                                            lineparts = line.split(' ')[-1].strip()[1]
                                            if lineparts == '0':
                                                door_status = "Driver Door Closed"
                                            elif lineparts == '1': 
                                                door_status = "Driver Door Open"
                                        # Can add more if more ajar strings are found i.e Passenger/RearRight/RearLeft
                                        
                                        data_found = (timestamp, door_status, latitude, longitude)
                                        if data_found not in data_list_door_status and timestamp != "" and door_status != "":
                                            data_list_door_status.append(data_found)
                                    except: 
                                        logfunc(f'Error in {line}')
                                
                                #Done

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

    if len(data_list_brake_status) > 0:
        report = ArtifactHtmlReport("Brake Status")
        report.start_artifact_report(report_folder, f"Brake Status")
        report.add_script()
        data_headers_brake_status = ("Timestamp", "Brake Status", "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_brake_status, data_list_brake_status, pathname)
        report.end_artifact_report()

        tsvname = f'Brake Status'
        tsv(report_folder, data_headers_brake_status , data_list_brake_status, tsvname)
        
        tlactivity = 'Brake Status'
        timeline(report_folder, tlactivity, data_list_brake_status, data_headers_brake_status)

    else:
        logfunc("No Brake Status info Available")

    if len(data_list_engine_temp) > 0:
        report = ArtifactHtmlReport("Engine Temp")
        report.start_artifact_report(report_folder, f"Engine Temp")
        report.add_script()
        data_headers_engine_temp = ("Timestamp", "Engine Temp Degrees Celcius", "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_engine_temp, data_list_engine_temp, pathname)
        report.end_artifact_report()

        tsvname = f'Engine Temp'
        tsv(report_folder, data_headers_engine_temp, data_list_engine_temp, tsvname)
        
        tlactivity = 'Engine Temp'
        timeline(report_folder, tlactivity, data_list_engine_temp, data_headers_engine_temp)

    else:
        logfunc("No Engine Temp info Available")

    if len(data_list_interior_temp) > 0:
        report = ArtifactHtmlReport("Interior Temp")
        report.start_artifact_report(report_folder, f"Interior Temp")
        report.add_script()
        data_headers_interior_temp = ("Timestamp", "Interior Temp Degrees Celcius", "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_interior_temp, data_list_interior_temp, pathname)
        report.end_artifact_report()

        tsvname = f'Interior Temp'
        tsv(report_folder, data_headers_interior_temp, data_list_interior_temp, tsvname)
        
        tlactivity = 'Interior Temp'
        timeline(report_folder, tlactivity, data_list_interior_temp, data_headers_interior_temp)

    else:
        logfunc("No Interior Temp info Available")

    if len(data_list_tp) > 0:
        report = ArtifactHtmlReport("Tire Pressure")
        report.start_artifact_report(report_folder, f"Tire Pressure")
        report.add_script()
        data_headers_tp = ("Timestamp", "Tire","Tire Pressure", "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_tp, data_list_tp, pathname)
        report.end_artifact_report()

        tsvname = f'Tire Pressure'
        tsv(report_folder, data_headers_tp, data_list_tp, tsvname)
        
        tlactivity = 'Tire Pressure'
        timeline(report_folder, tlactivity, data_list_tp, data_headers_tp)

    else:
        logfunc("No Tire Pressure info Available")

    if len(data_list_gear_state) > 0:
        report = ArtifactHtmlReport("Gear State")
        report.start_artifact_report(report_folder, f"Gear State")
        report.add_script()
        data_headers_gear_state = ("Timestamp", "Gear State ", "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_gear_state, data_list_gear_state, pathname)
        report.end_artifact_report()

        tsvname = f'Gear State'
        tsv(report_folder, data_headers_gear_state, data_list_gear_state, tsvname)
        
        tlactivity = 'Gear State'
        timeline(report_folder, tlactivity, data_list_gear_state, data_headers_gear_state)

    else:
        logfunc("No Gear State info Available")

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
        
    if len(data_list_door_status) > 0:
        report = ArtifactHtmlReport('Door Status')
        report.start_artifact_report(report_folder, f'Door Status')
        report.add_script()
        data_headers_door_status = ('Timestamp', 'Door Status', "Latitude", "Longitude")
        pathname = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers_door_status, data_list_door_status, pathname)
        report.end_artifact_report()
        
        tsvname = f'Door Status'
        tsv(report_folder, data_headers_door_status , data_list_door_status, tsvname)
        
        tlactivity = 'Door Status'
        timeline(report_folder, tlactivity, data_list_door_status, data_headers_door_status)
        
    else:
        logfunc(f'No Door Statuses available')

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
        "Tar_GZ_checker": (
                "Tar_GZ_checker",
                ('*/[H-M]_*.tar.gz'),
                get_TarGz)
}