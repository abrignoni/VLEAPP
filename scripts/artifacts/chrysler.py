import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['FCA','Jeep Cherokee']
platforms = ['Carplay']

def get_btDevices():
    print("nothing")

def get_contacts():
    print("nothing")

def get_calllogs():
    print("nothing")

def get_gpsdata():
    print("nothing")



__artifacts__ = {
    "bluetooth_devices": (
        "bluetooth devices",
        ('*/com.android.cooldata/databases/database*.db'),
        get_btDevices),
    "contacts": (
        "contacts",
        ('*/com.android.cooldata/files/cool.xml'),
        get_contacts),
    "call_logs": (
        "call_logs",
        ('*/com.android.cooldata/files/cool.xml'),
        get_calllogs),
    "gps_data": (
        "gps_data",
        ('dir'),
        get_gpsdata)

    
}