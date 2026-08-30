#!/usr/bin/env python3
"""Unwrap a Berla iVe .iVa export into something VLEAPP can process.

An .iVa is a plain ZIP holding another ZIP, which in turn holds the vehicle's own
source files:

    <case>.iVa                        ZIP
      Summary.json                    SHA-256 of every inner file
      Vehicle.json                    vehicle and acquisition record
      <case>.zip                      ZIP
        DCASourceFilesUpload.zip      ZIP  <- the vehicle data VLEAPP wants
        AcquireDB.ive                 iVe's own parsed database, encrypted
        Manifest.json, ECUData.json, DLCData.json, CaseData.json, Audit.json

VLEAPP's seekers do not descend into nested archives, so pointing the tool at a .iVa
matches nothing and produces an empty report. This script lifts DCASourceFilesUpload.zip
out, verifies it against the SHA-256 iVe recorded for it, and leaves a zip that can be
passed straight to VLEAPP with -t zip.

    python3 admin/scripts/unwrap_berla_iva.py CASE.iVa -o outdir
    python3 vleapp.py -t zip -i outdir/DCASourceFilesUpload.zip -o reports

AcquireDB.ive is not unwrapped. It is iVe's parsed output rather than the vehicle's own
data, and it is encrypted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile

SOURCE_FILES_MEMBER = "DCASourceFilesUpload.zip"
COPY_CHUNK = 16 << 20


def _sha256_stream(fh) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = fh.read(COPY_CHUNK)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def _recorded_hashes(outer: zipfile.ZipFile) -> dict:
    """Filename -> SHA-256, from the Summary.json iVe writes beside the payload."""
    try:
        summary = json.loads(outer.read("Summary.json"))
    except KeyError:
        return {}
    return {e["Filename"]: e["Hashvalue"] for e in summary
            if e.get("Filename") and e.get("Hashvalue")}


def describe(outer: zipfile.ZipFile) -> None:
    """Print what the export says it is. Vehicle.json is plain JSON in the outer zip."""
    try:
        vehicle = json.loads(outer.read("Vehicle.json"))
    except KeyError:
        print("  (no Vehicle.json in this export)")
        return
    collection = vehicle.get("Collection", {})
    selected = collection.get("SelectedVehicle") or {}
    print(f"  vehicle      : {selected.get('VehicleDisplay') or '(not recorded)'}")
    if selected.get("Vin"):
        print(f"  VIN          : {selected['Vin']}")
    print(f"  collected    : {collection.get('CollectionDate') or '(not recorded)'}")
    acquisitions = collection.get("Acquisitions") or []
    print(f"  acquisitions : {len(acquisitions)}")
    for acq in acquisitions:
        counts = {k[3:]: v for k, v in acq.items() if k.startswith("Num") and v}
        state = acq.get("ErrorMessage") or "no error reported"
        print(f"     {acq.get('AcqDate', '')[:19]}  {acq.get('EcuName', '?')}"
              f"  {acq.get('AcqType', '?')}  {state}")
        if counts:
            print(f"        iVe parsed: {counts}")


def unwrap(iva_path: str, out_dir: str, verify: bool = True) -> str:
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(iva_path) as outer:
        print(f"opened {os.path.basename(iva_path)}")
        describe(outer)
        outer_recorded = _recorded_hashes(outer)

        inner_names = [n for n in outer.namelist() if n.lower().endswith(".zip")]
        if not inner_names:
            sys.exit("no inner .zip in this .iVa; nothing to unwrap")
        inner_name = inner_names[0]

        inner_path = os.path.join(out_dir, os.path.basename(inner_name))
        print(f"\nlifting {inner_name} -> {inner_path}")
        with outer.open(inner_name) as src, open(inner_path, "wb") as dst:
            shutil.copyfileobj(src, dst, COPY_CHUNK)

    with zipfile.ZipFile(inner_path) as inner:
        recorded = dict(outer_recorded)
        # Manifest.json inside carries the same hashes; disagreement is worth knowing.
        for name, value in _recorded_hashes_from_manifest(inner).items():
            if name in recorded and recorded[name].lower() != value.lower():
                sys.exit(f"the export disagrees with itself about {name}:\n"
                         f"  Summary.json  {recorded[name]}\n  Manifest.json {value}")
            recorded.setdefault(name, value)
        if SOURCE_FILES_MEMBER not in inner.namelist():
            sys.exit(f"{SOURCE_FILES_MEMBER} not present in {inner_name}; "
                     "this export may not carry the vehicle's source files")
        target = os.path.join(out_dir, SOURCE_FILES_MEMBER)
        print(f"lifting {SOURCE_FILES_MEMBER} -> {target}")
        with inner.open(SOURCE_FILES_MEMBER) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst, COPY_CHUNK)

    os.remove(inner_path)

    if verify:
        want = recorded.get(SOURCE_FILES_MEMBER)
        if not want:
            print("\nWARNING: the export records no SHA-256 for "
                  f"{SOURCE_FILES_MEMBER}, so the copy could not be verified")
        else:
            with open(target, "rb") as fh:
                got = _sha256_stream(fh)
            if got.lower() != want.lower():
                sys.exit(f"\nHASH MISMATCH for {SOURCE_FILES_MEMBER}\n"
                         f"  recorded by iVe : {want}\n  computed        : {got}")
            print(f"\nverified against the SHA-256 iVe recorded: {got}")

    size = os.path.getsize(target)
    with zipfile.ZipFile(target) as src_zip:
        members = len(src_zip.infolist())
    print(f"\nready: {target}")
    print(f"  {size:,} bytes, {members:,} members")
    print(f"\nrun VLEAPP against it with:\n  python3 vleapp.py -t zip -i \"{target}\" -o <report folder>")
    return target


def _recorded_hashes_from_manifest(inner: zipfile.ZipFile) -> dict:
    """Manifest.json inside the inner zip carries the same per-file hashes."""
    try:
        manifest = json.loads(inner.read("Manifest.json"))
    except KeyError:
        return {}
    return {i["filename"]: i["hash"] for i in manifest.get("items", [])
            if i.get("filename") and i.get("hash")}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unwrap a Berla iVe .iVa export into a zip VLEAPP can process.")
    parser.add_argument("iva", help="path to the .iVa export")
    parser.add_argument("-o", "--out", default="iva_unwrapped",
                        help="output directory (default: iva_unwrapped)")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip the SHA-256 check against the export's own manifest")
    args = parser.parse_args()

    if not os.path.isfile(args.iva):
        sys.exit(f"not a file: {args.iva}")
    unwrap(args.iva, args.out, verify=not args.no_verify)


if __name__ == "__main__":
    main()
