import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_callHistory():
    pass

__artifacts__ = {
    "call history": (
        "call history",
        ('*/bluetooth.DB_BMS/CH_*.db'),
        get_callHistory),
}