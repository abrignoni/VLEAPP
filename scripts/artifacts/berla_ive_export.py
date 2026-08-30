"""Berla iVe .iVa export: the acquisition record, and how to reach the vehicle data.

An .iVa is a ZIP whose payload is another ZIP, so VLEAPP's seekers cannot descend to
the vehicle's own files. Pointing the tool straight at a .iVa therefore matches nothing
and produces an empty report, which reads as though the vehicle held no data.

Vehicle.json sits uncompressed at the top of the export, so this artifact fires on that
and reports what the export says it holds, including iVe's own per-acquisition counts.
That turns the empty run into a record of what is present and names the step that
reaches it: admin/scripts/unwrap_berla_iva.py.
"""

import json
import os

from scripts.ilapfuncs import artifact_processor

__artifacts_v2__ = {
    "berla_ive_export": {
        "name": "Berla iVe Export Record",
        "description": "The vehicle and acquisition record an iVe .iVa export carries, "
                       "with one row per acquisition giving the module, the acquisition "
                       "type, the status iVe recorded and the counts iVe reported parsing.",
        "author": "@AlexisBrignoni, Claude",
        "version": "0.1",
        "creation_date": "2026-08-30",
        "last_update_date": "2026-08-30",
        "requirements": "none",
        "category": "Vehicle Acquisition",
        "notes": "From Vehicle.json at the top of a Berla iVe .iVa export. The .iVa is a "
                 "ZIP holding another ZIP, and the seekers do not descend into nested "
                 "archives, so running VLEAPP against a .iVa directly reaches only this "
                 "file and the vehicle's own data is not seen. Unwrap it first with "
                 "admin/scripts/unwrap_berla_iva.py, which lifts DCASourceFilesUpload.zip "
                 "out and verifies it against the SHA-256 the export records, then run "
                 "VLEAPP against that zip. The counts in these rows are what iVe reported "
                 "for its own parse; they are not produced by VLEAPP and this artifact does "
                 "not verify them. iVe's parsed database, AcquireDB.ive, is encrypted and "
                 "is not read. A row here records that an acquisition was attempted and "
                 "what the tool reported, not what the vehicle contains. Four columns "
                 "are uniform on a single-vehicle export and are kept because they "
                 "vary between exports and identify which unit the rows belong to: "
                 "Module, Driver and Collection Date each hold one value when a "
                 "collection covers one module, and VIN was empty on the tested "
                 "export because iVe carries the field but it was not populated "
                 "there, which is worth showing rather than hiding. Note what the "
                 "unwrapped export does and does not give you: iVe carries both the raw "
                 "image and the file set it extracted from the head unit's filesystems, "
                 "and VLEAPP reads only the extracted files. On the tested export those "
                 "filesystems are QNX6, which no filesystem type Sleuth Kit supports can "
                 "walk, so the raw image is not reachable with that tooling. It is "
                 "reachable with qnxprobe, which reads QNX6 superblocks directly and "
                 "writes the logical files to a zip; on the tested export that route "
                 "produced the same rows from the same bytes, and it also surfaced a "
                 "fourth QNX6 volume that the export did not carry extracted files "
                 "for.",
        "paths": ('*/Vehicle.json',),
        "sample_data": {
            "adams_ford_syncgen3_iva": "Berla iVe export, Ford Sync Gen3 | 4 rows",
            "ford_syncg4_logical": "Ford Sync G4 | 0 rows, not an iVe export",
        },
        "output_types": "standard",
        "artifact_icon": "car",
    },
}


def _is_ive_export(payload):
    """True only for the shape an iVe Vehicle.json has.

    Vehicle.json is a common enough name that the glob alone would admit unrelated
    files, so this fails closed on anything that does not carry iVe's own structure.
    """
    if not isinstance(payload, dict):
        return False
    collection = payload.get("Collection")
    if not isinstance(collection, dict):
        return False
    return ("SelectedVehicle" in collection and "Acquisitions" in collection
            and isinstance(collection.get("Acquisitions"), list))


@artifact_processor
def berla_ive_export(context):
    data_list = []
    source_paths = []
    for file_found in context.get_files_found():
        file_found = str(file_found)
        if os.path.isdir(file_found):
            continue
        try:
            with open(file_found, 'r', encoding='utf-8', errors='replace') as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            continue
        if not _is_ive_export(payload):
            continue

        source_paths.append(file_found)
        collection = payload["Collection"]
        vehicle = collection.get("SelectedVehicle") or {}
        display = vehicle.get("VehicleDisplay") or ''
        vin = vehicle.get("Vin") or ''
        collected = collection.get("CollectionDate") or ''

        for acq in collection["Acquisitions"]:
            if not isinstance(acq, dict):
                continue
            counts = {k[3:]: v for k, v in acq.items()
                      if k.startswith("Num") and isinstance(v, int) and v}
            data_list.append((
                (acq.get("AcqDate") or '').replace('T', ' ')[:19],
                display, vin,
                acq.get("EcuName") or '', acq.get("AcqType") or '',
                acq.get("ErrorMessage") or 'no error reported',
                acq.get("PercentageComplete") if acq.get("PercentageComplete") is not None else '',
                ', '.join(f'{k} {v}' for k, v in sorted(counts.items())) or 'none reported',
                acq.get("DriverName") or '', acq.get("AcqUnit") or '',
                collected, context.get_relative_path(file_found)))

    data_headers = (('Acquisition Date', 'datetime'), 'Vehicle', 'VIN',
                    'Module', 'Acquisition Type', 'Status (as stored)',
                    'Percent Complete (as stored)', 'Counts iVe Reported',
                    'Driver (as stored)', 'Acquisition Unit (as stored)',
                    'Collection Date', 'Source File')
    return data_headers, data_list, '\n'.join(source_paths)
