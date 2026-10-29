"""Build a synthetic BMW NBT nav/ fixture for the bmw_nbt_navigation test case.

Nothing here is copied from evidence. The table definitions are those of the tested unit's
trails.sqlite and trips.sqlite (schema only), and every row, time and coordinate is made up:
the positions trace a short loop around 48.1770 N, 11.5560 E, chosen only to be a plausible
place on land. Path blobs are written in the record grammar bmw_nbt_navigation.py reads.

Usage:  python make_bmw_nbt_fixture.py OUT_DIR
Writes  OUT_DIR/bmw_nbt_fixture.zip         one unit:  NBT-HDD/p2/nav/{trails,trips}.sqlite
                                             plus a decoy NBT-HDD/p2/nav/trails.sqlite.bak
        OUT_DIR/bmw_nbt_fixture_multi/       two units (unit_a, unit_b) and the decoy, for the
                                             doubling check with check_artifact_output --compare
"""

import os
import shutil
import sqlite3
import struct
import sys
import zipfile

UNITS = 2 ** 32 / 360

TRAILS_SCHEMA = (
    "CREATE TABLE Description(Name TEXT PRIMARY KEY,Value BLOB)",
    "CREATE TABLE Trails( TrailId INTEGER PRIMARY KEY, DriverId INTEGER, RoadNetworkRelation INTEGER, "
    "Length INTEGER, BeginCoordinatedUniversalTime INTEGER, EndCoordinatedUniversalTime INTEGER, "
    "BeginLocalTime INTEGER, EndLocalTime INTEGER, Bounding BLOB, Path BLOB, Valid INTEGER DEFAULT 1, "
    "DurationTime INTEGER)",
)
TRIPS_SCHEMA = (
    "CREATE TABLE Description(Name TEXT PRIMARY KEY,Value BLOB)",
    "CREATE TABLE Trips(TripId INTEGER PRIMARY KEY, Source INTEGER, Mode INTEGER, RoadNetworkRelation "
    "INTEGER, BackwardReferences BLOB, DriverIds BLOB, Length INTEGER, DepartureCoordinatedUniversalTime "
    "INTEGER, ArrivalCoordinatedUniversalTime INTEGER, DepartureLocalTime INTEGER, ArrivalLocalTime "
    "INTEGER, Locations BLOB, Parameters BLOB, Bounding BLOB, Path BLOB, Valid INTEGER DEFAULT 1, "
    "BmwAdasStreetTypes INTEGER, CountryCodes BLOB, RoadClasses INTEGER, DurationTime INTEGER)",
    "CREATE TABLE Trails(TrailId INTEGER PRIMARY KEY, ForwardReferences BLOB, ProcessingState INTEGER)",
    "CREATE TABLE LinkToTripIndexTiles(TileId INTEGER PRIMARY KEY, LinkToTripIndex BLOB)",
)


def rec(tag, dist, payload=b''):
    return struct.pack('<BI', tag, dist) + payload


def pos(tag, dist, lat, lon):
    return rec(tag, dist, struct.pack('<ii', round(lon * UNITS), round(lat * UNITS)))


def tick(dist, ms):
    return rec(0x02, dist, struct.pack('<I', ms))


def path(records, begin_local, end_local, truncate=False):
    body = (rec(0x22, 0, b'\x03') + rec(0x20, 0, b'\x06')
            + rec(0x03, 0, struct.pack('<III', 0, begin_local, end_local))
            + rec(0x23, 0, b'USA') + rec(0x24, 0, b'\x01') + b''.join(records))
    if truncate:  # an unknown tag mid-stream: the grammar must stop and say where
        body += b'\xee' + b'\x00' * 12
    length = 16 + len(body) + 4
    return b'\x0a\x01\x01\x00\x01\x00' + struct.pack('<I', length) + b'\x00' * 12 + body + struct.pack('<I', length)


# A loop of made-up positions; (tag, distance, lat, lon) and the time ticks between them.
LOOP = [(48.17700, 11.55600), (48.17712, 11.55631), (48.17731, 11.55660), (48.17745, 11.55702),
        (48.17730, 11.55741), (48.17705, 11.55722), (48.17690, 11.55680), (48.17699, 11.55610)]


def trail_one():
    r = [pos(0x1e, 0, *LOOP[0]), tick(0, 0), tick(0, 4000)]
    dist = 0
    for i, (lat, lon) in enumerate(LOOP[1:], start=1):
        dist += 2500
        r.append(pos(0x1d if i % 2 else 0x1e, dist, lat, lon))
        r.append(rec(0x1f, dist, struct.pack('<I', 39000)))
        r.append(rec(0x07, dist, struct.pack('<h', -100)))
        r.append(tick(dist, 4000 + i * 3000))
    r.append(rec(0x16, dist))
    r.append(rec(0x14, dist))
    return r, dist


def build_unit(root, offset_ids=0):
    nav = os.path.join(root, 'p2', 'nav')
    os.makedirs(nav, exist_ok=True)
    begin = 1700000000 + offset_ids * 86400       # 2023-11-14 22:13:20 UTC
    local = begin - 3600                          # a made-up one-hour offset
    t1, d1 = trail_one()
    # trail 2: positions after the last tick (remain untimed), both tags, repeated position
    t2 = [pos(0x1e, 0, 48.17699, 11.55610), tick(0, 0), pos(0x1d, 900, 48.17705, 11.55590),
          tick(900, 2500), pos(0x1e, 1500, 48.17710, 11.55570), pos(0x1e, 1500, 48.17710, 11.55570)]
    # trail 3: Path that stops at an unknown tag after one position
    t3 = [pos(0x1d, 0, 48.17710, 11.55570), tick(0, 0)]
    trails = [
        (101 + offset_ids, 5, 1, d1 + 300, begin, begin + 26, local, local + 26, path(t1, local, local + 26), 26000),
        (102 + offset_ids, 4, 1, 1600, begin + 600, begin + 603, local + 600, local + 603,
         path(t2, local + 600, local + 603), 3100),
        (103 + offset_ids, 0, 1, 0, begin + 900, begin + 900, local + 900, local + 900,
         path(t3, local + 900, local + 900, truncate=True), 0),
    ]
    db = sqlite3.connect(os.path.join(nav, 'trails.sqlite'))
    for s in TRAILS_SCHEMA:
        db.execute(s)
    db.executemany('INSERT INTO Trails (TrailId, DriverId, RoadNetworkRelation, Length, '
                   'BeginCoordinatedUniversalTime, EndCoordinatedUniversalTime, BeginLocalTime, '
                   'EndLocalTime, Bounding, Path, Valid, DurationTime) VALUES (?,?,?,?,?,?,?,?,NULL,?,1,?)',
                   trails)
    db.commit()
    db.close()
    db = sqlite3.connect(os.path.join(nav, 'trips.sqlite'))
    for s in TRIPS_SCHEMA:
        db.execute(s)
    db.execute('INSERT INTO Trips (TripId, Source, Mode, RoadNetworkRelation, DriverIds, Length, '
               'DepartureCoordinatedUniversalTime, ArrivalCoordinatedUniversalTime, DepartureLocalTime, '
               'ArrivalLocalTime, Path, Valid, DurationTime) VALUES (?,0,0,1,?,?,?,?,?,?,?,1,?)',
               (11 + offset_ids, struct.pack('<II', 1, 5), d1 + 300, begin, begin + 26, local,
                local + 26, path(t1, local, local + 26), 26000))
    db.execute('INSERT INTO Trips (TripId, Source, Mode, RoadNetworkRelation, DriverIds, Length, '
               'DepartureCoordinatedUniversalTime, ArrivalCoordinatedUniversalTime, DepartureLocalTime, '
               'ArrivalLocalTime, Path, Valid, DurationTime) VALUES (?,0,0,1,?,?,?,?,?,?,?,1,?)',
               (12 + offset_ids, struct.pack('<III', 2, 5, 0), 1600, begin + 600, begin + 603,
                local + 600, local + 603, path(t2, local + 600, local + 603), 3100))
    db.execute('INSERT INTO Trails VALUES (?, NULL, 2)', (101 + offset_ids,))
    db.commit()
    db.close()
    # a decoy the glob admits but the module must ignore: same layout, different file name
    shutil.copy(os.path.join(nav, 'trails.sqlite'), os.path.join(nav, 'trails.sqlite.bak'))


def main():
    out = sys.argv[1]
    single = os.path.join(out, 'bmw_nbt_fixture_single')
    multi = os.path.join(out, 'bmw_nbt_fixture_multi')
    for d in (single, multi):
        shutil.rmtree(d, ignore_errors=True)
    build_unit(os.path.join(single, 'NBT-HDD'))
    build_unit(os.path.join(multi, 'unit_a', 'NBT-HDD'))
    build_unit(os.path.join(multi, 'unit_b', 'NBT-HDD'), offset_ids=1000)
    zpath = os.path.join(out, 'bmw_nbt_fixture.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(single):
            for f in sorted(files):
                full = os.path.join(base, f)
                info = zipfile.ZipInfo(os.path.relpath(full, single).replace(os.sep, '/'),
                                       date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                with open(full, 'rb') as stream:
                    z.writestr(info, stream.read())
    print('wrote', zpath, 'and', multi)


if __name__ == '__main__':
    main()
