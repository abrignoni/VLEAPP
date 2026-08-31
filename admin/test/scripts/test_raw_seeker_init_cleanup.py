"""Pin that a raw or iVa seeker whose __init__ fails after mkdtemp removes its
staging directory instead of orphaning it.

FileSeekerRaw and FileSeekerIva create a staging directory (tempfile.mkdtemp) as
their first action, then extract the image into it. If that extraction raises or
is interrupted (Ctrl-C on a slow run), __init__ never binds an object, so the
seeker's cleanup() can never reach the staging directory. Each __init__ therefore
removes it in a finally when the build does not complete; a build that succeeds
keeps the directory for cleanup() to remove at end of run.

The test patches mkdtemp to record the exact directory a build creates, so the
assertion is about that directory rather than the shared temp folder, and a
concurrent seeker on the same machine cannot make it pass or fail by accident.
"""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import scripts.search_files  # pylint: disable=wrong-import-position
from scripts.search_files import FileSeekerIva, FileSeekerRaw  # pylint: disable=wrong-import-position


class TestStagingDirCleanupOnInitFailure(unittest.TestCase):
    """A staging directory must not outlive a failed or interrupted seeker build."""

    def setUp(self):
        self.data_folder = tempfile.mkdtemp(prefix='vleapp_test_data_')
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

    def tearDown(self):
        for path in self.created:
            shutil.rmtree(path, ignore_errors=True)
        shutil.rmtree(self.data_folder, ignore_errors=True)

    def _assert_staging_removed(self):
        self.assertEqual(len(self.created), 1,
                         'expected the build to create exactly one staging directory')
        self.assertFalse(os.path.exists(self.created[0]),
                         'the staging directory was left behind after a failed build')

    def test_raw_extraction_error_removes_staging_dir(self):
        with mock.patch.object(scripts.search_files, '_extract_image_volumes',
                               side_effect=RuntimeError('extraction failed')):
            with self.assertRaises(RuntimeError):
                FileSeekerRaw('/nonexistent/image.img', self.data_folder)
        self._assert_staging_removed()

    def test_raw_keyboard_interrupt_removes_staging_dir(self):
        with mock.patch.object(scripts.search_files, '_extract_image_volumes',
                               side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                FileSeekerRaw('/nonexistent/image.img', self.data_folder)
        self._assert_staging_removed()

    def test_iva_bad_archive_removes_staging_dir(self):
        broken = os.path.join(self.data_folder, 'broken.iVa')
        with open(broken, 'wb') as handle:
            handle.write(b'not a zip archive')
        with self.assertRaises(Exception):
            FileSeekerIva(broken, self.data_folder)
        self._assert_staging_removed()


if __name__ == '__main__':
    unittest.main()
