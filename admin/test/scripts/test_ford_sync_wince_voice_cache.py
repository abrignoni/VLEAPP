"""The Ford SYNC voice name cache reader, against files built here.

No extraction is used: the layout is written out by hand so the reader's length checks
can be exercised, including the cases a real file was not seen to hold.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.artifacts.ford_sync_wince_voice_cache import _entries  # noqa: E402


def _record(name, spoken, number, slack=b''):
    spoken_bytes = spoken.encode('latin-1') + b'\x00\x00'
    padded = spoken_bytes + b'\x00' * (len(spoken_bytes) % 2)
    name_bytes = name.encode('utf-16-le') + b'\x00\x00'
    body = padded + struct.pack('<HH', number, len(name_bytes)) + name_bytes + slack
    return struct.pack('<HHBBH', 8 + len(body), 1, 1, 1, len(spoken_bytes)) + body


def _cache(records, count=None, tail=True):
    body = b''.join(records)
    if tail:
        body += b'\x00\x00' * (len(records) + 1)
    count = len(records) if count is None else count
    return struct.pack('<IHH', 8 + len(body), 2000, count) + body


class VoiceNameCacheTest(unittest.TestCase):

    def test_reads_every_entry_with_even_and_odd_string_lengths(self):
        data = _cache([_record('Ada Example', '#ab#', 1), _record('Bo', '#abc#', 0)])
        entries, count, problem = _entries(data)
        self.assertEqual(problem, '')
        self.assertEqual(count, 2)
        self.assertEqual(entries, [('Ada Example', '#ab#', 1, 1), ('Bo', '#abc#', 0, 2)])

    def test_bytes_after_the_name_inside_a_record_are_not_read_as_name(self):
        data = _cache([_record('Ada', '#a#', 0, slack=b'X\x00Y\x00\x00\x00'), _record('Bo', '#b#', 1)])
        entries, _count, problem = _entries(data)
        self.assertEqual(problem, '')
        self.assertEqual([entry[0] for entry in entries], ['Ada', 'Bo'])

    def test_a_size_field_that_is_not_the_file_size_reads_nothing(self):
        data = _cache([_record('Ada', '#a#', 0)]) + b'\x00'
        entries, count, problem = _entries(data)
        self.assertEqual(entries, [])
        self.assertEqual(count, 1)
        self.assertIn('states a size', problem)

    def test_a_count_larger_than_the_records_keeps_what_was_read(self):
        data = _cache([_record('Ada', '#a#', 0)], count=3, tail=False)
        entries, count, problem = _entries(data)
        self.assertEqual([entry[0] for entry in entries], ['Ada'])
        self.assertEqual(count, 3)
        self.assertIn('entry 2', problem)

    def test_a_name_length_past_its_record_stops_the_read(self):
        good = _record('Ada', '#a#', 0)
        bad = bytearray(_record('Bo', '#b#', 1))
        struct.pack_into('<H', bad, 8 + 6 + 2, 400)   # the name length, after a 6-byte string
        entries, _count, problem = _entries(_cache([good, bytes(bad)]))
        self.assertEqual([entry[0] for entry in entries], ['Ada'])
        self.assertIn('entry 2', problem)

    def test_a_file_shorter_than_its_header(self):
        self.assertEqual(_entries(b'\x00\x00\x00'), ([], 0, 'shorter than its header'))


if __name__ == '__main__':
    unittest.main()
