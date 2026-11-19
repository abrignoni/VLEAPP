"""GM OnStar LG generation 9 var/sysinfo/gps.dat fixes, against files built here.

No extraction is used. The positions and times are invented; only the layout is the one
read from a generation 9 unit: an 8-byte header, ten 80-byte slots newest first, and the
<SysInfo1.00> tag at offset 816 of an 831-byte file.
"""
import os
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.artifacts.gm_onstar_lg import (  # noqa: E402
    _gen9_fixes, _gps_to_utc, gm_onstar_lg_gen9_gps_fixes)

GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)


def _slot(utc, latitude, longitude, leap=18, stored_leap=None, byte_56=9):
    """An 80-byte slot for a fix at utc, its stored time written with stored_leap."""
    gps = utc + timedelta(seconds=leap)
    since = gps - GPS_EPOCH
    week = since.days // 7
    tow_ms = round((since - timedelta(weeks=week)).total_seconds() * 1000)
    stored = gps - timedelta(seconds=stored_leap if stored_leap is not None else leap)
    seconds = stored.second + stored.microsecond / 1e6
    slot = bytearray(80)
    struct.pack_into('>I', slot, 0, 0x4891B400)
    struct.pack_into('>HBBBBHf', slot, 4, stored.year, stored.month, stored.day, stored.hour,
                     stored.minute, 0, seconds)
    struct.pack_into('>dd', slot, 16, latitude * 1e7, longitude * 1e7)
    slot[56] = byte_56
    struct.pack_into('>H', slot, 60, week)
    struct.pack_into('>I', slot, 64, tow_ms)
    return bytes(slot)


def _file(slots):
    data = bytearray(b'\x48\x92\x20\x20\xff\xff\xff\xff')
    for slot in slots:
        data += slot
    data += bytes(80 * (10 - len(slots)))
    data += b'\x00\x00\x00\x0a\x00\x00\x00\x00'
    data += b'<SysInfo1.00>\x00\x82'
    assert len(data) == 831
    return bytes(data)


def _track(start, count, step=15):
    """count fixes 15 seconds apart, newest first as the module writes them."""
    fixes = [(start + timedelta(seconds=step * i), 10.0 + i * 0.001, 20.0 - i * 0.001)
             for i in range(count)]
    return list(reversed(fixes))


class _Context:
    def __init__(self, files):
        self.files = files

    def get_files_found(self):
        return self.files

    @staticmethod
    def get_relative_path(path):
        return os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path)


class Gen9GpsFixesTest(unittest.TestCase):

    def test_leap_seconds_follow_the_date(self):
        day_ms = 86400000
        week_2017 = (datetime(2017, 1, 2, tzinfo=timezone.utc) - GPS_EPOCH).days // 7
        self.assertEqual(_gps_to_utc(week_2017, 3 * day_ms)[1], 18)
        # Week 2017-01-01 begins at GPS midnight, which is still 2016 in UTC.
        self.assertEqual(_gps_to_utc(week_2017, 0)[1], 17)
        week_2014 = (datetime(2014, 3, 3, tzinfo=timezone.utc) - GPS_EPOCH).days // 7
        self.assertEqual(_gps_to_utc(week_2014, 3 * day_ms)[1], 16)

    def test_slots_are_read_with_both_times(self):
        start = datetime(2024, 5, 6, 7, 8, 9, 500000, tzinfo=timezone.utc)
        data = _file([_slot(t, la, lo) for t, la, lo in _track(start, 10)])
        fixes, left_out = _gen9_fixes(data)
        self.assertEqual(left_out, 0)
        self.assertEqual(len(fixes), 10)
        slot, stored, utc, offset, latitude, longitude, _week, _tow, byte_56 = fixes[-1]
        self.assertEqual(slot, 10)
        self.assertEqual(utc, start)
        self.assertEqual(stored, start)
        self.assertEqual(offset, 18)
        self.assertEqual((latitude, longitude, byte_56), (10.0, 20.0, 9))

    def test_a_stale_stored_count_is_shown_not_trusted(self):
        start = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
        data = _file([_slot(start, 10.0, 20.0, stored_leap=15)])
        _slot_no, stored, utc, _offset, *_rest = _gen9_fixes(data)[0][0]
        self.assertEqual(utc, start)
        self.assertEqual(stored - utc, timedelta(seconds=3))

    def test_empty_slots_are_left_out_and_counted(self):
        start = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
        fixes, left_out = _gen9_fixes(_file([_slot(start, 10.0, 20.0)]))
        self.assertEqual((len(fixes), left_out), (1, 9))

    def test_other_layouts_are_refused(self):
        start = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
        data = _file([_slot(start, 10.0, 20.0)])
        self.assertIsNone(_gen9_fixes(data[:-1]))
        self.assertIsNone(_gen9_fixes(data.replace(b'<SysInfo1.00>', b'<SysInfo2.00>')))
        self.assertIsNone(_gen9_fixes(b'[*]\r\nTimeStamp=01-14-26 17:50:00\r\n'))

    def test_fixes_across_copies_are_listed_once_with_times_found(self):
        start = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
        track = _track(start, 14)
        older = _file([_slot(t, la, lo) for t, la, lo in track[4:14]])
        newer = _file([_slot(t, la, lo) for t, la, lo in track[0:10]])
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for relative, data in (('$Deleted/$NoFolder/gps.dat.deleted-000001', older),
                                   ('sysinfo/gps.dat', newer),
                                   ('var/sysinfo/gps.dat', newer)):
                path = os.path.join(folder, *relative.split('/'))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as handle:
                    handle.write(data)
                paths.append(path)
            headers, rows, source = gm_onstar_lg_gen9_gps_fixes.__wrapped__(_Context(paths))
        names = [h[0] if isinstance(h, tuple) else h for h in headers]
        self.assertEqual(len(rows), 14)
        times = [row[names.index('Timestamp')] for row in rows]
        self.assertEqual(times, sorted(times))
        found = {row[names.index('Timestamp')]: row[names.index('Times Found')] for row in rows}
        # Six fixes are in all three files, four only in the older, four only in the newer two.
        self.assertEqual(sorted(found.values()), [1] * 4 + [2] * 4 + [3] * 6)
        self.assertEqual(len(source.split('\n')), 2)


if __name__ == '__main__':
    unittest.main()
