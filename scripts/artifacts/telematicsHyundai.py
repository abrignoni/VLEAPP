import os


from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, kmlgen, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Santa Fe',]
platforms = ['Android Automotive',]

def get_telematicsHyundai(files_found, report_folder, seeker, wrap_text):
    initLastGpsDetail = []
    wdwStatus = []
    weatherWaypoint = []
    EngineIdleAlarmTask = []
    driving = []
    Provisioning = []
    can = []
    for file_found in files_found:
        file_found = str(file_found)
        
        with open(file_found, 'r') as f:
            lines = f.readlines()
            filename = os.path.basename(file_found)
            location = os.path.dirname(file_found)
            for line in lines:
                #print(line)
                if line.startswith(' <Boot'):
                    continue
                else:
                    timestamp = line.split(' ', 2)
                    timestamp = f"XXXX-{timestamp[0]} {timestamp[1]}"
                    
                    if 'initLastGpsDetail' in line:
                        splits = line.split(' ')
                        speed = (splits[18].split('Speed:')[1])
                        head = ((splits[18].split('Speed:')[0].split('Head:')[1]))
                        latitude = (splits[15])
                        longitude = (splits[16].split(':')[1])
                        altitude = (splits[17].split(':')[1])
                        time = (splits[19].split(':')[1])
                        year = time[0:4]
                        month = time[4:6]
                        day = time[6:8]
                        hour = time[8:10]
                        minute = time[10:12]
                        seconds = time[12::]
                        fecha = f'{year}-{month}-{day} {hour}:{minute}:{seconds}'
                        offset = (splits[20].split(':')[1])
                        
                        initLastGpsDetail.append((timestamp,fecha,offset,latitude,longitude,head,speed,filename))
                        
                    if 'wdwStatus' in line:
                        splits = line.split(' ')
                        descriptor = (splits[13])
                        latitude = (splits[16].split()[4])
                        longitude = (splits[16].split()[5])
                        
                        wdwStatus.append((timestamp,descriptor,latitude,longitude))
                        
                    if 'Address_name' in line:
                        add1 = (line.split('Address_name :')[1].split(',',2)[0])
                        add2 = (line.split('Address_name :')[1].split(',',2)[1])
                        add = f'{add1} {add2}'
                        
                        weatherWaypoint.append((timestamp,add))
                        
                    if 'EngineIdleAlarmTask' in line:
                        event = (line.split('[EngineIdleAlarmTask] ')[1])
                        
                        EngineIdleAlarmTask.append((timestamp,event))
                        
                    if '[DRIVING] ' in line:
                        event = (line.split('[DRIVING]')[1])
                        
                        driving.append((timestamp,event))
                        
                        
                    if '[Provisioning]' in line:
                        event = (line.split(' '))
                        
                        vin = (event[15].split(':')[1])
                        mdn = (event[16].split(':')[1])
                        min = (event[17].split(':')[1])
                        
                        Provisioning.append((timestamp,vin,mdn,min))
                        
                    if '[CAN]' in line:
                        event = line.split('[CAN]')[1]
                        
                        can.append((timestamp,event))
                    
            
    if len(initLastGpsDetail) > 0:
        report = ArtifactHtmlReport('GPS Detail')
        report.start_artifact_report(report_folder, f'GPS Detail')
        report.add_script()
        data_headers = ('Timestamp','Date','Date Offset','Latitude','Longitude','Head','Speed','Source')
        report.write_artifact_data_table(data_headers, initLastGpsDetail, location)
        report.end_artifact_report()
        
        tsvname = f'GPS Detail'
        tsv(report_folder, data_headers, initLastGpsDetail, tsvname)
        
        kmlactivity = 'GPS Detail'
        kmlgen(report_folder, kmlactivity, initLastGpsDetail, data_headers)
        
        
    else:
        logfunc(f'No GPS Detail data available')
    
    
    if len(wdwStatus) > 0:
        report = ArtifactHtmlReport('WdwStatus Report')
        report.start_artifact_report(report_folder, f'WdwStatus Report')
        report.add_script()
        data_headers = ('Timestamp','Descriptor','Latitude','Longitude')
        report.write_artifact_data_table(data_headers, wdwStatus, location)
        report.end_artifact_report()
        
        tsvname = f'WdwStatus Report'
        tsv(report_folder, data_headers, wdwStatus, tsvname)
        
        kmlactivity = 'WdwStatus Report'
        kmlgen(report_folder, kmlactivity, wdwStatus, data_headers)
        
    else:
        logfunc(f'No WdwStatus Report data available')
        
    
    if len(weatherWaypoint) > 0:
        report = ArtifactHtmlReport('WeatherWaypoint Address')
        report.start_artifact_report(report_folder, f'WeatherWaypoint Address')
        report.add_script()
        data_headers = ('Timestamp','Address')
        report.write_artifact_data_table(data_headers, weatherWaypoint, location)
        report.end_artifact_report()
        
        tsvname = f'WeatherWaypoint Address'
        tsv(report_folder, data_headers, weatherWaypoint, tsvname)
        
    else:
        logfunc(f'No WeatherWaypoint Report data available')
        

    if len(EngineIdleAlarmTask) > 0:
        report = ArtifactHtmlReport('EngineIdleAlarmTask Events')
        report.start_artifact_report(report_folder, f'EngineIdleAlarmTask Events')
        report.add_script()
        data_headers = ('Timestamp','Events')
        report.write_artifact_data_table(data_headers, EngineIdleAlarmTask, location)
        report.end_artifact_report()
        
        tsvname = f'EngineIdleAlarmTask Address'
        tsv(report_folder, data_headers, EngineIdleAlarmTask, tsvname)
        
    else:
        logfunc(f'No EngineIdleAlarmTask Report data available')
        
        
    if len(driving) > 0:
        report = ArtifactHtmlReport('Driving Events')
        report.start_artifact_report(report_folder, f'Driving Events')
        report.add_script()
        data_headers = ('Timestamp','Events')
        report.write_artifact_data_table(data_headers, driving, location)
        report.end_artifact_report()
        
        tsvname = f'Driving Events'
        tsv(report_folder, data_headers, driving, tsvname)
        
    else:
        logfunc(f'No Driving Report data available')
        
    
    if len(can) > 0:
        report = ArtifactHtmlReport('CAN Events')
        report.start_artifact_report(report_folder, f'CAN Events')
        report.add_script()
        data_headers = ('Timestamp','Events')
        report.write_artifact_data_table(data_headers, can, location)
        report.end_artifact_report()
        
        tsvname = f'CAN Events'
        tsv(report_folder, data_headers, can, tsvname)
        
    else:
        logfunc(f'No CAN Report data available')
        
    
    if len(can) > 0:
        report = ArtifactHtmlReport('Provisioning Events')
        report.start_artifact_report(report_folder, f'Provisioning Events')
        report.add_script()
        data_headers = ('Timestamp','VIN','MDM','MIN')
        report.write_artifact_data_table(data_headers, Provisioning, location)
        report.end_artifact_report()
        
        tsvname = f'Provisioning Events'
        tsv(report_folder, data_headers, Provisioning, tsvname)
        
    else:
        logfunc(f'No Provisioning Report data available')
        


__artifacts__ = {
        "Telematics": (
                "Telematics",
                ('*/telematics.log*'),
                get_telematicsHyundai)
}