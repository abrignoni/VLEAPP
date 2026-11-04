"""BMW NBT framing, time semantics, provenance and independent-unit controls."""
# pylint: disable=protected-access

import hashlib
import inspect
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.artifacts import bmw_nbt_navigation as nbt  # pylint: disable=wrong-import-position
from admin.test.scripts.make_bmw_nbt_fixture import build_unit  # pylint: disable=wrong-import-position


def framed(body):
    """A hand-built frame, independent of the fixture writer and decoder constants."""
    length = len(body) + 20
    return (b'\x0a\x01\x01\x00\x01\x00' + struct.pack('<I', length)
            + bytes(12) + body + struct.pack('<I', length))


def position(longitude=0x10000000, latitude=0x20000000):
    return b'\x1d' + struct.pack('<Iii', 17, longitude, latitude)


def clock(milliseconds):
    return b'\x02' + struct.pack('<II', 17, milliseconds)


def context_for(paths, base):
    return SimpleNamespace(
        get_files_found=lambda: paths,
        get_relative_path=lambda value: Path(value).relative_to(base).as_posix())


class PathTests(unittest.TestCase):
    """Expected numbers below are fixed answers, not derived by the parser."""

    def test_signed_coordinates_and_millisecond_time(self):
        points, status = nbt._decode_path(framed(position(-0x10000000) + clock(1234)))
        self.assertEqual(status, 'Yes')
        self.assertEqual(points, [(0, 0x1d, 17, -0x10000000, 0x20000000, 1234)])
        self.assertEqual(nbt._degrees(points[0][3]), -22.5)
        self.assertEqual(nbt._latitude(points[0][4]), 45.0)
        self.assertEqual(nbt._utc(1700000000, 1234),
                         datetime(2023, 11, 14, 22, 13, 21, 234000, timezone.utc))

    def test_first_following_tick_times_all_pending_positions(self):
        points, status = nbt._decode_path(framed(position() * 2 + clock(2500) + clock(5000)))
        self.assertEqual(status, 'Yes')
        self.assertEqual([point[5] for point in points], [2500, 2500])

    def test_trailing_positions_remain_untimed_on_complete_frame(self):
        points, status = nbt._decode_path(framed(clock(2500) + position() * 2))
        self.assertEqual(status, 'Yes')
        self.assertEqual([point[5] for point in points], [None, None])

    def test_following_clock_times_only_positions_that_precede_it(self):
        points, status = nbt._decode_path(framed(position() + clock(2500) + position()))
        self.assertEqual(status, 'Yes')
        self.assertEqual([point[5] for point in points], [2500, None])

    def test_missing_tick_preserves_position_without_inventing_time(self):
        points, status = nbt._decode_path(framed(position()))
        self.assertIn('no time record', status)
        self.assertIsNone(points[0][5])
        self.assertEqual(nbt._utc(1700000000, points[0][5]), '')

    def test_unknown_tag_retains_timed_points_but_not_unestablished_time(self):
        points, status = nbt._decode_path(framed(position() + clock(2500)
                                                + position() + b'\xee' + bytes(12)))
        self.assertIn('tag 0xee', status)
        self.assertEqual([point[5] for point in points], [2500, None])

    def test_short_payload_is_reported_without_hiding_earlier_positions(self):
        points, status = nbt._decode_path(framed(position() + clock(1000) + b'\x1d\0'))
        self.assertIn('tag 0x1d', status)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0][5], 1000)

    def test_bad_trailer_does_not_assign_pending_time(self):
        blob = framed(clock(1000) + position())
        points, status = nbt._decode_path(blob[:-4] + bytes(4))
        self.assertIn('trailing length', status)
        self.assertEqual(len(points), 1)
        self.assertIsNone(points[0][5])

    def test_unsupported_framing_is_rejected(self):
        good = framed(position() + clock(1000))
        variants = [None, b'', good[:20], b'\xff' + good[1:],
                    good[:6] + bytes(4) + good[10:],
                    good[:10] + b'\x01' + good[11:]]
        for blob in variants:
            with self.subTest(blob=repr(blob)[:50]):
                points, status = nbt._decode_path(blob)
                self.assertEqual(points, [])
                self.assertTrue(status.startswith('No:'))

    def test_invalid_latitude_is_not_mapped(self):
        self.assertEqual(nbt._latitude(0x60000000), '')
        self.assertEqual(nbt._latitude(0x40000000), 90.0)
        self.assertEqual(nbt._latitude(-0x40000000), -90.0)

    def test_zero_invalid_and_missing_dates_are_blank(self):
        for value in (None, 0, '', 'invalid', 10**30, float('nan')):
            with self.subTest(value=value):
                self.assertEqual(nbt._utc(value), '')
                self.assertEqual(nbt._as_recorded(value), '')

    def test_local_clock_remains_unzoned_and_keeps_milliseconds(self):
        self.assertEqual(nbt._as_recorded(1700000000, 2500), '2023-11-14 22:13:22.500')

    def test_driver_ids_count_and_raw_fallback(self):
        self.assertEqual(nbt._driver_ids(struct.pack('<III', 2, 5, 0)), '5, 0')
        self.assertEqual(nbt._driver_ids(struct.pack('<I', 0)), '')
        self.assertEqual(nbt._driver_ids(b'\x02\x00\x00\x00\xff'), '02000000ff')
        self.assertEqual(nbt._driver_ids(None), '')


class StoreTests(unittest.TestCase):
    """Exercise real SQLite readers and the undecorated artifact entry points."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.unit = self.root / 'unit_a' / 'NBT-HDD'
        build_unit(str(self.unit))
        self.nav = self.unit / 'p2' / 'nav'
        self.logs = patch.object(nbt, 'logfunc')
        self.log_mock = self.logs.start()
        self.addCleanup(self.logs.stop)

    def run_artifact(self, name, paths):
        return inspect.unwrap(getattr(nbt, name))(context_for(paths, self.root))

    def test_fixture_counts_relative_sources_and_ignored_backup(self):
        paths = [str(path) for path in self.nav.iterdir()]
        for name, expected in (('bmw_nbt_trail_points', 13),
                               ('bmw_nbt_trails', 3), ('bmw_nbt_trips', 2)):
            with self.subTest(artifact=name):
                headers, rows, sources = self.run_artifact(name, paths)
                self.assertEqual(len(rows), expected)
                self.assertTrue(all(len(row) == len(headers) for row in rows))
                self.assertTrue(all(row[-1].startswith('unit_a/NBT-HDD/') for row in rows))
                self.assertNotIn('.bak', sources)

    def test_same_source_repeated_does_not_duplicate_rows(self):
        source = str(self.nav / 'trails.sqlite')
        _, rows, sources = self.run_artifact('bmw_nbt_trail_points', [source] * 2)
        self.assertEqual(len(rows), 13)
        self.assertEqual(sources, source)

    def test_source_selection_follows_os_case_normalization(self):
        files = ['/unit/nav/TRAILS.SQLITE', '/unit/nav/trails.sqlite.bak']
        with patch.object(nbt.os.path, 'normcase', side_effect=str.lower):
            self.assertEqual(nbt._source_paths(context_for(files, self.root), 'trails.sqlite'),
                             ['/unit/nav/TRAILS.SQLITE'])

    def test_two_units_with_colliding_ids_keep_separate_rows_and_sources(self):
        other = self.root / 'unit_b' / 'NBT-HDD'
        build_unit(str(other))
        paths = [str(self.nav / 'trails.sqlite'), str(other / 'p2/nav/trails.sqlite')]
        _, rows, sources = self.run_artifact('bmw_nbt_trail_points', paths)
        self.assertEqual(len(rows), 26)
        self.assertEqual({row[4] for row in rows}, {101, 102, 103})
        self.assertEqual({row[-1] for row in rows},
                         {'unit_a/NBT-HDD/p2/nav/trails.sqlite',
                          'unit_b/NBT-HDD/p2/nav/trails.sqlite'})
        self.assertEqual(len(sources.splitlines()), 2)

    def test_missing_table_retains_source_and_logs_failure(self):
        empty = self.root / 'empty' / 'trails.sqlite'
        empty.parent.mkdir()
        sqlite3.connect(empty).close()
        for name in ('bmw_nbt_trails', 'bmw_nbt_trail_points'):
            with self.subTest(artifact=name):
                _, rows, sources = self.run_artifact(name, [str(empty)])
                self.assertEqual(rows, [])
                self.assertEqual(sources, str(empty))
        self.assertTrue(self.log_mock.called)

    def test_no_tick_outputs_blank_time_and_retains_stored_coordinates(self):
        source = self.nav / 'trails.sqlite'
        with sqlite3.connect(source) as db:
            db.execute('DELETE FROM Trails')
            db.execute('INSERT INTO Trails (TrailId, BeginCoordinatedUniversalTime, '
                       'BeginLocalTime, Path) VALUES (1,1700000000,1700000000,?)',
                       (framed(position()),))
        _, rows, _ = self.run_artifact('bmw_nbt_trail_points', [str(source)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:4], ('', '', 45.0, 22.5))
        self.assertEqual(rows[0][8:10], (0x20000000, 0x10000000))

    def test_trailing_rows_keep_coordinates_with_blank_utc_and_local_times(self):
        source = str(self.nav / 'trails.sqlite')
        _, rows, _ = self.run_artifact('bmw_nbt_trail_points', [source])
        trailing = [row for row in rows if row[4] == 102 and row[5] in (9, 10)]
        self.assertEqual(len(trailing), 2)
        self.assertTrue(all(row[0] == '' and row[1] == '' for row in trailing))
        self.assertTrue(all(row[2] != '' and row[3] != '' for row in trailing))

    def test_reader_preserves_database_bytes(self):
        sources = [self.nav / 'trails.sqlite', self.nav / 'trips.sqlite']
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
        for name in ('bmw_nbt_trail_points', 'bmw_nbt_trails', 'bmw_nbt_trips'):
            self.run_artifact(name, [str(path) for path in sources])
        self.assertEqual(before,
                         {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources})

    def test_uncheckpointed_wal_rows_are_read_without_changing_database_or_wal(self):
        source = self.nav / 'trails.sqlite'
        writer = sqlite3.connect(source)
        self.addCleanup(writer.close)
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute('INSERT INTO Trails (TrailId, DriverId, Length, '
                       'BeginCoordinatedUniversalTime, EndCoordinatedUniversalTime, '
                       'BeginLocalTime, EndLocalTime, DurationTime, Path) '
                       'SELECT 104, DriverId, Length, BeginCoordinatedUniversalTime, '
                       'EndCoordinatedUniversalTime, BeginLocalTime, EndLocalTime, '
                       'DurationTime, Path FROM Trails WHERE TrailId=101')
        writer.commit()
        files = [source, Path(str(source) + '-wal')]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        _, rows, sources = self.run_artifact('bmw_nbt_trail_points', [str(path) for path in files])
        self.assertEqual(len(rows), 21)
        self.assertEqual(sum(row[4] == 104 for row in rows), 8)
        self.assertEqual(sources, str(source))
        self.assertEqual(before,
                         {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files})


if __name__ == '__main__':
    unittest.main()
