import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Ford Mustang','F-150']
platforms = ['SYNC3.2V2','SYNCGen3.0_3.0.18093_PRODUC T']

def get_btDevices(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:
        with open(file_found, "r") as f:
            devaddval = manuval = devmodval = supprofval = phonedownval = ''
            availcodecval = servsupval = subscribenumval = netnameval = ''
            devsoftval = devfriendval = classdevval = chldval = inbandval = ''
            for line in f:
                splits = line.split(':',1)
                totalvalues = len(splits)
                if totalvalues > 1:
                    key = splits[0].strip()
                    value = splits[1].strip()
                    if  key == 'Device Address' :
                        devaddval = value
                    if  key == 'Manufacturer' :
                        manuval = value.strip('"')
                    if  key == 'Device Model' :
                        devmodval = value
                    if  key == 'SupportedProfiles' :
                        supprofval = value
                    if  key == 'Phonebook Download Support' :
                        phonedownval = value    
                    if  key == 'Available Codec' :
                        availcodecval = value    
                    if  key == 'Service Supported' :
                        servsupval = value    
                    if  key == 'subscriberNum' :
                        subscribenumval = value    
                    if  key == 'networkName' :
                        netnameval = value    
                    if  key == 'deviceSoftwareVersion' :
                        devsoftval = value    
                    if  key == 'Device Friendly Name' :
                        devfriendval = value    
                    if  key == 'Class Of Device' :
                        classdevval = value    
                    if  key == 'CHLD capabilities' :
                        chldval = value    
                else:
                    if 'BRSF' in splits[0]:
                        brsfval = splits[0].strip()
                    if 'CHLD' in splits[0]:
                        eqsplit = splits[0].split('=')
                        chldval = eqsplit[1].strip()
                    if 'In-Band' in splits[0]:
                        inbandval = splits[0].strip()
                    if 'Phonebook' in splits[0]:
                        phonedownval = splits[0].strip()
        data_list.append((devmodval,manuval,subscribenumval,devfriendval,devaddval,devsoftval,netnameval,supprofval,classdevval,servsupval,availcodecval,phonedownval,chldval,brsfval,inbandval))
            
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Bluetooth Devices')
        report.start_artifact_report(report_folder, f'Bluetooth Devices')
        report.add_script()
        data_headers = ('Device Model','Manufacturer','Subscriber Number','Device Friendly Name','Device Address','Device Software Version','Network Name','Supported Profiles','Class of Device','Service Supported','Available Codec','Phonebook Download Support','CHLD Capabilities','BRSF','In-Band')
        file_found = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'Bluetooth Devices'
        tsv(report_folder, data_headers, data_list, tsvname)
        
    else:
        logfunc(f'No Bluetooth Devices available')


__artifacts__ = {
        "Bluetooth": (
                "Bluetooth",
                ('*/BT/devlog_*.txt'),
                get_btDevices)
}