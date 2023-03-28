import os
import gzip
import datetime

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, kmlgen, logdevinfo, is_platform_windows, timeline

#Compatability Data
vehicles = ['Kia Sorrento 2018',]
platforms = ['Unknown',]

def timestampcalc(timevalue):
    timestamp = (datetime.datetime.fromtimestamp(int(timevalue)/1000).strftime('%Y-%m-%d %H:%M:%S'))
    return timestamp

def get_systemappwtf(files_found, report_folder, seeker, wrap_text):
    data_list_gps = []
    data_list = []
    
    for file_found in files_found:
        file_found = str(file_found)
        
        filename = os.path.basename(file_found)
        location = os.path.dirname(file_found)
        
        if file_found.endswith('.gz'):
            with gzip.open(file_found, 'rb') as f_in:
                file = f_in.readlines()
        else:
            with open(file_found, 'r') as f:
                file = f.readlines()
                
        for x in file:
            if isinstance(x, bytes):
                x = x.decode()
                
            if 'V/GpsLocationProvider' and 'reportLocation' in x:
                fecha = ' '.join(x.split(' ',2)[:2])
                limitedlineone = (x.split('reportLocation')[1])
                gpslatlong = limitedlineone.split('timestamp: ')[0]
                gpslong = gpslatlong.split('long: ')[1]
                middle = gpslatlong.split('long: ')[0]
                gpslat = middle.split('lat: ')[1]
                timestamp = limitedlineone.split('timestamp: ')[1]
                timestampfinal = timestampcalc(timestamp)
                
                data_list_gps.append((timestampfinal, fecha, gpslat, gpslong, file_found, x))
                
            if '[BTCallTracker] ' and 'number=' in x:
                fecha = ' '.join(x.split(' ',2)[:2])
                if 'GET_CURRENT_CALLS  'in x:
                    currentcalls = x.split('GET_CURRENT_CALLS  ')[1]
                    
                    numberone = (currentcalls.split(',', 11))[8]
                    number = (numberone.split('=')[1])
                    
                    status = (currentcalls.split(',', 11))[1]
                    
                    print(fecha,number,'NULL',status)
                    
                if '[BTCallTracker] poll: conn' in x:
                    datacall = x.split('addr: ')[1]
                    number = datacall.split(' ',1)[0]
                    
                    incoming = (datacall.split(' ',5)[2])
                    state = (datacall.split(' ',5)[4])
                    
                    data_list.append((fecha,number,incoming,state,file_found,x))
            
                    
            
    if len(data_list_gps) > 0:
        report = ArtifactHtmlReport('GPS Detail')
        report.start_artifact_report(report_folder, f'GPS Detail')
        report.add_script()
        data_headers_gps = ('Timestamp','Date','Latitude','Longitude','Source','Source Line')
        report.write_artifact_data_table(data_headers_gps, data_list_gps, location)
        report.end_artifact_report()
        
        tsvname = f'GPS Detail'
        tsv(report_folder, data_headers_gps, data_list_gps, tsvname)
        
        kmlactivity = 'GPS Detail'
        kmlgen(report_folder, kmlactivity, data_list_gps, data_headers_gps)
        
        tlactivity = 'GPS Detail'
        timeline(report_folder, tlactivity, data_list_gps, data_headers_gps)
    
    else:
        logfunc(f'No GPS Detail data available')
    
    
    if len(data_list) > 0:
        report = ArtifactHtmlReport('BT Call Report')
        report.start_artifact_report(report_folder, f'BT Call Report')
        report.add_script()
        data_headers = ('Date','Phone Number','Incoming','State','Source','Source Line')
        report.write_artifact_data_table(data_headers, data_list, location)
        report.end_artifact_report()
        
        tsvname = f'BT Call Report'
        tsv(report_folder, data_headers, data_list, tsvname)

    else:
        logfunc(f'No BT Call Report data available')
        
    
__artifacts__ = {
        "BT Report": (
                "BT Report",
                ('*/system_app_wtf@*.txt.gz','*/tombstones/tombstone_*','*/system_app_crash@*.txt.gz','*/SYSTEM_TOMBSTONE@*.txt.gz'),
                get_systemappwtf)
}