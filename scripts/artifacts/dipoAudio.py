import xml.etree.ElementTree as ET
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Santa Fe',]
platforms = ['Android Automotive',]

def get_dipoAudio(files_found, report_folder, seeker, wrap_text, time_offset):
    data_list = []
    for file_found in files_found:

        tree = ET.parse(file_found)
        root = tree.getroot()
        
        for elem in root:
            name = (elem.attrib['name'])
            if name == 'pref_key_local_bt_address':
                text = elem.text
            else:
                text = ''
            data_list.append((name,text))
            
    if len(data_list) > 0:
        report = ArtifactHtmlReport('Audio UUIDs')
        report.start_artifact_report(report_folder, f'Audio UUIDs')
        report.add_script()
        data_headers = ('UUID','Extra Value')
        #file_found = os.path.dirname(file_found)
        report.write_artifact_data_table(data_headers, data_list, file_found)
        report.end_artifact_report()
        
        tsvname = f'Audio UUIDs'
        tsv(report_folder, data_headers, data_list, tsvname)
        
    else:
        logfunc(f'No Audio UUIDs available')


__artifacts__ = {
        "dipoAudio": (
                "Audio UUIDs",
                ('*/com.daudio.app.dipo/shared_prefs/pref_dipo.xml'),
                get_dipoAudio)
}