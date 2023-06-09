import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_devices():
    pass

__artifacts__ = {
    "connected devices": (
        "connected devices",
        ('*/wireless_dev_list.dat'),
        get_devices),
}