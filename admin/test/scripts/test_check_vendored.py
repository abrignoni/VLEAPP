"""Pin what admin/scripts/check_vendored.py treats as drift.

The guard compares each vendored file against the hash recorded in
scripts/vendor/vendored.json, and optionally against a checkout of the upstream
repository. A changed byte has to fail and a matching file has to pass.

It also pins the split between the two outcomes. An upstream checkout that does
not hold the file was never compared, so it is reported under its own headline
and its own exit code rather than as drift. That exit code still has to be
non-zero: an upstream that cannot be read must never read as a pass.

Everything here runs against a temporary tree, never the network.
"""
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / 'admin' / 'scripts' / 'check_vendored.py'

_spec = importlib.util.spec_from_file_location('check_vendored', SCRIPT)
check_vendored = importlib.util.module_from_spec(_spec)
sys.modules['check_vendored'] = check_vendored
_spec.loader.exec_module(check_vendored)

BODY = b'"""A vendored module."""\n\nVALUE = 1\n'


class CheckVendoredTest(unittest.TestCase):
    """The two outcomes, and the exit code each one uses."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / 'scripts' / 'vendor').mkdir(parents=True)
        self.vendored = self.root / 'scripts' / 'vendor' / 'module.py'
        self.vendored.write_bytes(BODY)
        self.upstream = self.root / 'upstream'
        self.upstream.mkdir()
        (self.upstream / 'module.py').write_bytes(BODY)

        import hashlib
        self.manifest_path = self.root / 'scripts' / 'vendor' / 'vendored.json'
        self._write_manifest(hashlib.sha256(BODY).hexdigest())

        self._repo, self._manifest = check_vendored.REPO, check_vendored.MANIFEST
        check_vendored.REPO = str(self.root)
        check_vendored.MANIFEST = str(self.manifest_path)
        self.addCleanup(setattr, check_vendored, 'REPO', self._repo)
        self.addCleanup(setattr, check_vendored, 'MANIFEST', self._manifest)

    def _write_manifest(self, digest):
        self.manifest_path.write_text(json.dumps({'vendored': [{
            'path': 'scripts/vendor/module.py', 'name': 'example', 'version': '1.0',
            'upstream': 'https://github.com/example/example', 'upstream_file': 'module.py',
            'commit': '0123456789abcdef0123456789abcdef01234567', 'sha256': digest,
        }]}), encoding='utf-8')

    def _run(self, argv=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = check_vendored.main(argv or [])
        return rc, buf.getvalue()

    def test_matching_file_passes(self):
        rc, out = self._run()
        self.assertIn('all matching what was recorded', out)
        self.assertEqual(rc, 0)

    def test_one_changed_byte_is_drift(self):
        self.vendored.write_bytes(BODY.replace(b'VALUE = 1', b'VALUE = 2'))
        rc, out = self._run()
        self.assertIn('have drifted', out)
        self.assertNotIn('could not be checked', out)
        self.assertEqual(rc, 1)

    def test_missing_file_is_drift(self):
        self.vendored.unlink()
        rc, out = self._run()
        self.assertIn('recorded in the manifest but not on disk', out)
        self.assertEqual(rc, 1)

    # ---- "could not check" is not "has drifted" -------------------------------

    def test_upstream_without_the_file_is_blocked_not_drift(self):
        """Nothing was compared, so this is not evidence about the copy."""
        rc, out = self._run(['--upstream', str(self.root / 'no-such-checkout')])
        self.assertIn('could not be checked', out)
        self.assertNotIn('have drifted', out)
        self.assertEqual(rc, 2)

    def test_blocked_run_is_never_a_pass(self):
        """Exit 0 here would let a missing checkout silently stop guarding the file."""
        rc, _ = self._run(['--upstream', str(self.root / 'no-such-checkout')])
        self.assertNotEqual(rc, 0)

    def test_upstream_that_moved_on_is_drift_not_blocked(self):
        """The comparison did happen, so this one is a finding."""
        (self.upstream / 'module.py').write_bytes(BODY.replace(b'VALUE = 1', b'VALUE = 3'))
        rc, out = self._run(['--upstream', str(self.upstream)])
        self.assertIn('upstream has moved on', out)
        self.assertIn('have drifted', out)
        self.assertNotIn('could not be checked', out)
        self.assertEqual(rc, 1)

    def test_matching_upstream_passes(self):
        rc, out = self._run(['--upstream', str(self.upstream)])
        self.assertIn('and matches the upstream checkout', out)
        self.assertEqual(rc, 0)

    def test_drift_outranks_blocked_when_both_happen(self):
        """One file drifted and one upstream unreadable: report both, exit 1."""
        import hashlib
        other = self.root / 'scripts' / 'vendor' / 'other.py'
        other.write_bytes(BODY)
        manifest = json.loads(self.manifest_path.read_text())
        entry = dict(manifest['vendored'][0])
        entry.update(path='scripts/vendor/other.py', upstream_file='other.py',
                     sha256=hashlib.sha256(BODY).hexdigest())
        manifest['vendored'].append(entry)
        manifest['vendored'][0]['sha256'] = 'deadbeef' * 8
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

        rc, out = self._run(['--upstream', str(self.upstream)])
        self.assertIn('have drifted', out)
        self.assertIn('could not be checked', out)
        self.assertEqual(rc, 1)

    def test_the_real_manifest_matches_the_files_on_disk(self):
        """This repo's own vendored files, checked without the network."""
        check_vendored.REPO, check_vendored.MANIFEST = self._repo, self._manifest
        manifest = json.loads(pathlib.Path(self._manifest).read_text(encoding='utf-8'))
        self.assertTrue(manifest['vendored'])
        for entry in manifest['vendored']:
            path = pathlib.Path(self._repo) / entry['path']
            self.assertTrue(path.is_file(), entry['path'])
            self.assertEqual(check_vendored.sha256(str(path)), entry['sha256'], entry['path'])


if __name__ == '__main__':
    unittest.main()
