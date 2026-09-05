"""Pin the guard around reading one segment of a split raw image.

FTK Imager and its peers write a raw image as numbered segments (.001, .002,
...) unless told to write one file. The first segment alone carries the
partition table and the boot volumes, so the vendored reader identifies it
cleanly and reads its front volumes correctly, while every volume past the cut
reads as empty with nothing raised. Measured on a Ford Sync G4 image cut at
1,500 MB: the boot partitions extracted in full and the 28.8 GiB storage volume
reported 0 files, 0 B, failed 0.

Since qnxprobe 1.13 the reader joins every segment of the set beside the file
it is given, so a split image is handed to it as it is. What VLEAPP adds is the
run log: split_image_sibling() recognises a numbered segment with its successor
beside it and FileSeekerRaw says the set will be joined, and
_warn_incomplete_volumes() repeats what the reader recorded in volumes.json,
the segments it joined and any volume the image turned out too short for.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import scripts.search_files  # pylint: disable=wrong-import-position
from scripts.search_files import (  # pylint: disable=wrong-import-position
    FileSeekerRaw, _warn_incomplete_volumes, split_image_sibling)


class TestSplitImageSibling(unittest.TestCase):
    """A numbered suffix with the next number beside it is a split image."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='vleapp_test_split_')
        self.addCleanup(shutil.rmtree, self.folder, True)

    def touch(self, name):
        path = os.path.join(self.folder, name)
        with open(path, 'wb') as handle:
            handle.write(b'x')
        return path

    def test_first_segment_with_its_successor(self):
        first = self.touch('image.001')
        second = self.touch('image.002')
        self.assertEqual(split_image_sibling(first), second)

    def test_first_segment_alone_is_an_image(self):
        first = self.touch('image.001')
        self.assertIsNone(split_image_sibling(first))

    def test_a_gap_is_not_a_successor(self):
        first = self.touch('image.001')
        self.touch('image.003')
        self.assertIsNone(split_image_sibling(first))

    def test_middle_segment_is_still_a_segment(self):
        second = self.touch('image.002')
        third = self.touch('image.003')
        self.assertEqual(split_image_sibling(second), third)

    def test_width_is_kept_across_the_carry(self):
        ninth = self.touch('image.009')
        tenth = self.touch('image.010')
        self.assertEqual(split_image_sibling(ninth), tenth)

    def test_double_extension_keeps_the_stem(self):
        first = self.touch('image.dd.001')
        second = self.touch('image.dd.002')
        self.assertEqual(split_image_sibling(first), second)

    def test_a_conventional_extension_is_not_a_segment(self):
        image = self.touch('image.img')
        self.touch('image.002')
        self.assertIsNone(split_image_sibling(image))

    def test_a_bare_numbered_name_is_not_a_segment(self):
        self.assertIsNone(split_image_sibling(self.touch('.001')))


class TestRawSeekerHandsASegmentToTheReader(unittest.TestCase):
    """A segment with its successor beside it is read, and the log says so."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='vleapp_test_split_')
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_first_segment_with_successor_is_read_and_logged(self):
        first = os.path.join(self.folder, 'image.001')
        for name in ('image.001', 'image.002'):
            with open(os.path.join(self.folder, name), 'wb') as handle:
                handle.write(b'x')
        with mock.patch.object(scripts.search_files, '_extract_image_volumes') as extract, \
                mock.patch.object(scripts.search_files.FileSeekerZip, '__init__',
                                  return_value=None), \
                mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            seeker = FileSeekerRaw(first, self.folder)
        self.addCleanup(shutil.rmtree, seeker._stage_dir, True)  # pylint: disable=protected-access
        extract.assert_called_once()
        self.assertEqual(extract.call_args.args[1], first)
        logged = '\n'.join(str(call.args[0]) for call in logfunc.call_args_list)
        self.assertIn('image.002 sits beside it', logged)
        self.assertIn('joins every segment', logged)

    def test_a_lone_image_draws_no_split_message(self):
        image = os.path.join(self.folder, 'image.img')
        with open(image, 'wb') as handle:
            handle.write(b'x')
        with mock.patch.object(scripts.search_files, '_extract_image_volumes'), \
                mock.patch.object(scripts.search_files.FileSeekerZip, '__init__',
                                  return_value=None), \
                mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            seeker = FileSeekerRaw(image, self.folder)
        self.addCleanup(shutil.rmtree, seeker._stage_dir, True)  # pylint: disable=protected-access
        logged = '\n'.join(str(call.args[0]) for call in logfunc.call_args_list)
        self.assertNotIn('split image', logged)


class TestIncompleteVolumeWarning(unittest.TestCase):
    """What the reader recorded about a cut image reaches the run log."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='vleapp_test_split_')
        self.addCleanup(shutil.rmtree, self.folder, True)

    def staged(self, manifest):
        path = os.path.join(self.folder, 'qnx_volumes.zip')
        with zipfile.ZipFile(path, 'w') as archive:
            if manifest is not None:
                archive.writestr('volumes.json', json.dumps(manifest))
        return path

    def test_incomplete_volume_is_logged_by_name(self):
        manifest = {'written_by': 'qnxprobe 1.12', 'volumes': [
            {'volume': 'p3_lba16384_dps_mfg', 'files': 23, 'short': 0},
            {'volume': 'p9_lba737280_storage', 'files': 0, 'short': 0,
             'extends_past_image_by_bytes': 29695668224},
            {'volume': 'p6_lba81920_ifs', 'files': 700, 'short': 2},
        ]}
        with mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            incomplete = _warn_incomplete_volumes(self.staged(manifest))
        self.assertEqual([v['volume'] for v in incomplete],
                         ['p9_lba737280_storage', 'p6_lba81920_ifs'])
        logged = '\n'.join(str(call.args[0]) for call in logfunc.call_args_list)
        self.assertIn('WARNING', logged)
        self.assertIn('p9_lba737280_storage: reaches 29,695,668,224 bytes', logged)
        self.assertIn('p6_lba81920_ifs', logged)
        self.assertIn('2 cut short', logged)
        self.assertNotIn('dps_mfg', logged)

    def test_complete_volumes_stay_quiet(self):
        manifest = {'written_by': 'qnxprobe 1.12', 'volumes': [
            {'volume': 'p3_lba16384_dps_mfg', 'files': 23, 'short': 0}]}
        with mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            self.assertEqual(_warn_incomplete_volumes(self.staged(manifest)), [])
        logfunc.assert_not_called()

    def test_joined_segments_are_logged_from_the_manifest(self):
        segments = [{'name': 'mmcblk0.img.001', 'bytes': 1572864000},
                    {'name': 'mmcblk0.img.002', 'bytes': 1572864000},
                    {'name': 'mmcblk0.img.003', 'bytes': 1384120320}]
        manifest = {'written_by': 'qnxprobe 1.13', 'volumes': [
            {'volume': 'p3_lba16384_dps_mfg', 'image': 'mmcblk0.img.001',
             'image_segments': segments, 'files': 23, 'short': 0},
            {'volume': 'p9_lba737280_storage', 'image': 'mmcblk0.img.001',
             'image_segments': segments, 'files': 7362, 'short': 0}]}
        with mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            self.assertEqual(_warn_incomplete_volumes(self.staged(manifest)), [])
        logged = '\n'.join(str(call.args[0]) for call in logfunc.call_args_list)
        self.assertIn('3 segments joined in order, mmcblk0.img.001 .. mmcblk0.img.003, '
                      '4,529,848,320 bytes in all', logged)
        self.assertNotIn('WARNING', logged)

    def test_a_zip_without_a_manifest_stays_quiet(self):
        with mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            self.assertEqual(_warn_incomplete_volumes(self.staged(None)), [])
        logfunc.assert_not_called()


if __name__ == '__main__':
    unittest.main()
