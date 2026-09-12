"""Pin the Berla iVe .iVa seeker, which unwraps the export and reads what is inside.

An .iVa is a zip holding a zip holding DCASourceFilesUpload.zip, which carries the
vehicle's source files: a raw image under DiskImages/ when the acquisition took one,
otherwise the file set iVe extracted. FileSeekerIva unwraps into a temporary folder,
hands the image to FileSeekerRaw (or the file set to FileSeekerZip), and stages the
export's Vehicle.json as a member so the acquisition record is reported too.

The fixtures are built here from the NTFS test image under admin/test/data/raw_images/,
so a staged file is checked against the hash list an independent reader wrote for it.
"""
import gzip
import hashlib
import io
import os
import pathlib
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import scripts.search_files  # pylint: disable=wrong-import-position
from scripts.search_files import FileSeekerIva  # pylint: disable=wrong-import-position

FIXTURES = REPO_ROOT / 'admin' / 'test' / 'data' / 'raw_images'
VEHICLE = b'{"Vehicle": {"Make": "Test", "Model": "Fixture"}}'


def _hash_list(path):
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        digest, _, rel = line.partition('  ')
        if rel:
            out[rel.strip()] = digest.strip()
    return out


def _sha256(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _zip_bytes(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _with_mbr(volume_bytes, start_lba=2048):
    entry = bytearray(16)
    entry[4] = 0x07
    struct.pack_into("<II", entry, 8, start_lba, len(volume_bytes) // 512)
    mbr = bytearray(start_lba * 512)
    mbr[446:462] = entry
    mbr[510:512] = b"\x55\xaa"
    return bytes(mbr) + volume_bytes


class IvaSeekerTest(unittest.TestCase):
    """Both shapes of export, and the staging directory's lifetime."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix='iva_test_')
        with gzip.open(FIXTURES / 'ntfs-fixture.img.gz', 'rb') as src:
            cls.ntfs = src.read()
        cls.hashes = _hash_list(FIXTURES / 'ntfs-fixture.sha256')
        source_with_image = _zip_bytes({'DiskImages/mmcblk0.img': _with_mbr(cls.ntfs),
                                        'Extracted/note.txt': b'from the vendor export'})
        source_files_only = _zip_bytes({'Extracted/note.txt': b'from the vendor export',
                                        'Extracted/logs/one.log': b'log line'})
        cls.iva_image = os.path.join(cls.work, 'with_image.iVa')
        cls.iva_files = os.path.join(cls.work, 'files_only.iVa')
        for path, source in ((cls.iva_image, source_with_image), (cls.iva_files, source_files_only)):
            inner = _zip_bytes({'DCASourceFilesUpload.zip': source, 'ive.db': b'encrypted'})
            with open(path, 'wb') as out:
                out.write(_zip_bytes({'Vehicle.json': VEHICLE, 'CASE-1.zip': inner}))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def setUp(self):
        self.data = tempfile.mkdtemp(prefix='iva_data_')
        self.addCleanup(shutil.rmtree, self.data, True)
        self.created = []
        real_mkdtemp = tempfile.mkdtemp

        def recording_mkdtemp(*args, **kwargs):
            path = real_mkdtemp(*args, **kwargs)
            self.created.append(path)
            return path

        patcher = mock.patch.object(scripts.search_files.tempfile, 'mkdtemp',
                                    side_effect=recording_mkdtemp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True) for p in self.created])

    def test_an_export_with_an_image_is_read_through_the_image(self):
        seeker = FileSeekerIva(self.iva_image, self.data)
        try:
            found = seeker.search('*/many/file_0007.txt')
            self.assertEqual(len(found), 1)
            self.assertEqual(_sha256(found[0]), self.hashes['many/file_0007.txt'])
            self.assertEqual(seeker.file_infos[found[0]].source_path,
                             'p1_lba2048/many/file_0007.txt')
            vehicle = seeker.search('*/Vehicle.json')
            self.assertEqual(len(vehicle), 1)
            with open(vehicle[0], 'rb') as handle:
                self.assertEqual(handle.read(), VEHICLE)
            self.assertEqual(seeker.file_infos[vehicle[0]].source_path, 'Vehicle.json')
            self.assertEqual(seeker.search('*/Vehicle.json', return_on_first_hit=True), vehicle[0])
            # the extracted file set is not consulted when the image is there
            self.assertEqual(seeker.search('*/Extracted/note.txt'), [])
            self.assertTrue(os.path.isdir(self.created[0]), 'the image copy lives for the run')
        finally:
            seeker.cleanup()
        self.assertFalse(os.path.exists(self.created[0]), 'cleanup removes the staging directory')

    def test_an_export_without_an_image_reads_the_extracted_files(self):
        seeker = FileSeekerIva(self.iva_files, self.data)
        try:
            found = seeker.search('*/Extracted/logs/one.log')
            self.assertEqual(len(found), 1)
            with open(found[0], 'rb') as handle:
                self.assertEqual(handle.read(), b'log line')
            self.assertEqual(len(seeker.search('*/Vehicle.json')), 1)
            self.assertEqual(seeker.search('*/nothing/here'), [])
        finally:
            seeker.cleanup()
        self.assertFalse(os.path.exists(self.created[0]))

    def test_a_bad_archive_removes_the_staging_directory(self):
        broken = os.path.join(self.data, 'broken.iVa')
        with open(broken, 'wb') as handle:
            handle.write(b'not a zip archive')
        with self.assertRaises(Exception):
            FileSeekerIva(broken, self.data)
        self.assertEqual(len(self.created), 1)
        self.assertFalse(os.path.exists(self.created[0]),
                         'the staging directory was left behind after a failed build')

    def test_an_export_without_source_files_is_refused_by_name(self):
        path = os.path.join(self.work, 'no_source.iVa')
        with open(path, 'wb') as out:
            out.write(_zip_bytes({'Vehicle.json': VEHICLE,
                                  'CASE-1.zip': _zip_bytes({'ive.db': b'x'})}))
        with self.assertRaises(RuntimeError) as caught:
            FileSeekerIva(path, self.data)
        self.assertIn('DCASourceFilesUpload.zip', str(caught.exception))
        self.assertFalse(os.path.exists(self.created[0]))


if __name__ == '__main__':
    unittest.main()
