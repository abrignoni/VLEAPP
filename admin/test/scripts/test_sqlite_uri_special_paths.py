"""SQLite URIs built from a path keep working when the path holds '#' or '?'.

A URI such as f"file:{path}?mode=ro" ends the path at the first '#' (fragment) or
'?' (query). For a folder named "case #12" SQLite then opens "case " instead and the
tables read as absent. The reader below must percent-quote the path, so it reads
the synthetic database it was given and leaves no stray file next to the folder.
"""
# pylint: disable=protected-access

import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.artifacts import gm_ga130  # pylint: disable=wrong-import-position


class _Context:
    def __init__(self, files):
        self.files = files

    def get_files_found(self):
        return self.files


class SpecialCharacterPathTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        # "case " is where an unquoted URI for "case #1?x/..." lands.
        self.folder = os.path.join(self.root, 'case #1?x')
        os.makedirs(self.folder)
        self.stray = os.path.join(self.root, 'case ')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_gm_ga130_reads_its_temp_copy(self):
        # The module copies each database to its own mkstemp file, so a '#' in the
        # temp folder is what puts the character in the path.
        source = os.path.join(self.folder, 'synthetic.db')
        with sqlite3.connect(source) as db:
            db.execute('CREATE TABLE synthetic (value TEXT)')
            db.execute("INSERT INTO synthetic VALUES ('row')")
        db.close()
        rows = []
        with patch.object(tempfile, 'tempdir', self.folder):
            for _found, connection in gm_ga130._databases(_Context([source]), lambda _name: True):
                rows.extend(connection.execute('SELECT value FROM synthetic').fetchall())
        self.assertEqual(rows, [('row',)])
        self.assertFalse(os.path.exists(self.stray), 'the URI was cut at # or ?')


if __name__ == '__main__':
    unittest.main()
