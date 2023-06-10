import csv
import os

from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, logdevinfo, is_platform_windows

#Compatability Data
vehicles = ['Hyundai Sonata']
platforms = ['Carplay']

def get_contacts():
    pass

__artifacts__ = {
    "contacts": (
        "contacts",
        ('*/bluetooth/DB_BMS/MC_*.db'),
        get_contacts),
}