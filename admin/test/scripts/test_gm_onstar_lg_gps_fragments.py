"""GM OnStar LG Gen10 GPS reports read from fragments, against files built here.

No extraction is used. A fragment is a run of GPS report keys whose document opening
([*] and TimeStamp) was overwritten; the shapes below are the ones seen on flash images:
the GPSRegularReport header surviving, and the header gone with only the tail of the
key list left.
"""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.artifacts.gm_onstar_lg import (  # noqa: E402
    _gps_fragments, gm_onstar_lg_gps_reports)


def _hex(fmt, value):
    return ' '.join(f'{byte:02X}' for byte in struct.pack(fmt, value))


def _keys(lat, lon, tow, cog=True):
    lines = []
    if cog:
        lines.append(f'cog={_hex("<f", 12.5)}')
    lines += ['elevation=100', 'gps_tow=' + str(tow), 'gps_week=2401',
              f'hdop={_hex("<f", 1.5)}', f'lat={_hex("<d", lat)}', f'lon={_hex("<d", lon)}',
              f'sog={_hex("<f", 3.0)}', 'sv_used_cnt=9', 'utc_day=14', 'utc_hour=17',
              'utc_min=49', 'utc_month=1', f'utc_sec={_hex("<f", 42.0)}', 'utc_year=2026']
    return '\r\n'.join(lines) + '\r\n'


def _document(sections):
    body = '[*]\r\nTimeStamp=01-14-26 17:50:00\r\nVersion=1\r\n'
    for name, keys in sections:
        body += f'[{name}]\r\n{keys}'
    return body.encode('latin-1') + b'\x1a'


class _Context:
    def __init__(self, files):
        self.files = files

    def get_files_found(self):
        return self.files

    @staticmethod
    def get_relative_path(path):
        return os.path.basename(path)


class GpsFragmentTest(unittest.TestCase):

    def test_keys_inside_a_document_are_not_fragments(self):
        data = _document([('GPSRegularReport01', _keys(1e8, 2e8, 100))])
        self.assertEqual(_gps_fragments(data), [])

    def test_a_surviving_header_names_the_section(self):
        data = b'\x00junk\r\n[GPSRegularReport07]\r\n' + _keys(1e8, 2e8, 100).encode() + b'\x1a'
        fragments = _gps_fragments(data)
        self.assertEqual([(section, values['gps_tow']) for _o, section, values in fragments],
                         [('GPSRegularReport07', '100')])

    def test_a_headerless_tail_after_other_text_is_read(self):
        data = (b'other.dat Wed Jan 14 17:31:55 2026,1,0  97 52 04\r\n'
                + _keys(1e8, 2e8, 200, cog=False).encode())
        fragments = _gps_fragments(data)
        self.assertEqual(len(fragments), 1)
        offset, section, values = fragments[0]
        self.assertEqual(section, '')
        self.assertEqual(data[offset:offset + 10], b'elevation=')
        self.assertNotIn('cog', values)

    def test_a_key_run_without_a_position_is_not_a_report(self):
        data = b'\r\n[Other]\r\nlat=1\r\nname=x\r\n'
        self.assertEqual(_gps_fragments(data), [])

    def test_a_fragment_of_a_listed_report_adds_no_row(self):
        with tempfile.TemporaryDirectory() as folder:
            full = os.path.join(folder, 'gps.dat')
            with open(full, 'wb') as handle:
                handle.write(_document([('GPSRegularReport01', _keys(1e8, 2e8, 100))]))
            image = os.path.join(folder, 'NORimage.bin')
            with open(image, 'wb') as handle:
                handle.write(b'\xff' * 32 + b'\r\n' + _keys(1e8, 2e8, 100, cog=False).encode()
                             + b'\xff' * 32 + b'\r\n' + _keys(3e8, 4e8, 300, cog=False).encode())
            headers, rows, _paths = gm_onstar_lg_gps_reports.__wrapped__(
                _Context([full, image]))
        names = [h[0] if isinstance(h, tuple) else h for h in headers]
        table = [dict(zip(names, row)) for row in rows]
        by_tow = {row['GPS Time Of Week (as stored)']: row for row in table}
        self.assertEqual(sorted(by_tow), ['100', '300'])
        self.assertEqual((by_tow['100']['Read From'], by_tow['100']['Times Found'],
                          by_tow['100']['Section']), ('Document', 2, 'GPSRegularReport01'))
        self.assertEqual((by_tow['300']['Read From'], by_tow['300']['Section'],
                          by_tow['300']['Latitude'], by_tow['300']['Source File']),
                         ('Fragment', '', 30.0, 'NORimage.bin'))
        self.assertEqual(by_tow['300']['Timestamp'], '2026-01-14 17:49:42')


if __name__ == '__main__':
    unittest.main()
