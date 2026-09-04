"""Pin the guard around reading one segment of a split raw image.

FTK Imager and its peers write a raw image as numbered segments (.001, .002,
...) unless told to write one file. The first segment alone carries the
partition table and the boot volumes, so the vendored reader identifies it
cleanly and reads its front volumes correctly, while every volume past the cut
reads as empty with nothing raised. Measured on a Ford Sync G4 image cut at
1,500 MB: the boot partitions extracted in full and the 28.8 GiB storage volume
reported 0 files, 0 B, failed 0.

Three things stand between that and a report: split_image_sibling() recognises
a numbered segment with its successor beside it, FileSeekerRaw refuses such a
file before it stages anything, and _warn_incomplete_volumes() repeats in the
run log what qnxprobe 1.12 records in volumes.json when the image turns out to
be shorter than the volumes it describes.
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


class TestRawSeekerRefusesASegment(unittest.TestCase):
    """The refusal happens before anything is staged or the reader is started."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='vleapp_test_split_')
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_first_segment_with_successor_raises_before_staging(self):
        first = os.path.join(self.folder, 'image.001')
        for name in ('image.001', 'image.002'):
            with open(os.path.join(self.folder, name), 'wb') as handle:
                handle.write(b'x')
        with mock.patch.object(scripts.search_files.tempfile, 'mkdtemp') as mkdtemp, \
                mock.patch.object(scripts.search_files, '_extract_image_volumes') as extract:
            with self.assertRaises(ValueError) as caught:
                FileSeekerRaw(first, self.folder)
        self.assertIn('image.002', str(caught.exception))
        mkdtemp.assert_not_called()
        extract.assert_not_called()


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

    def test_a_zip_without_a_manifest_stays_quiet(self):
        with mock.patch.object(scripts.search_files, 'logfunc') as logfunc:
            self.assertEqual(_warn_incomplete_volumes(self.staged(None)), [])
        logfunc.assert_not_called()


if __name__ == '__main__':
    unittest.main()
