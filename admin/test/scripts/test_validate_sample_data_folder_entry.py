"""Pin how validate_sample_data.py treats a registry entry whose match path is a folder: accepted, with no hash,
only when the entry declares "input_type": "fs"; otherwise reported as missing, as before."""
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / 'admin' / 'scripts' / 'validate_sample_data.py'


def _load():
    spec = importlib.util.spec_from_file_location('validate_sample_data', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FolderEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vsd = _load()

    def check(self, entry):
        with tempfile.TemporaryDirectory() as root:
            (pathlib.Path(root) / 'Acquisition' / 'DiskImages').mkdir(parents=True)
            registry_path = pathlib.Path(root) / 'samples.json'
            registry = {'version': 1, 'samples': {'unit_folder': entry}}
            registry_path.write_text(json.dumps(registry))
            report = self.vsd.Report()
            self.vsd.check_registry({}, registry, registry_path, False, report)
            return report

    def test_a_folder_declared_fs_is_accepted_without_a_hash(self):
        report = self.check({'match': {'zip': 'Acquisition'}, 'input_type': 'fs'})
        self.assertEqual(report.errors, [])
        self.assertTrue(any('folder entry' in n for n in report.notes))

    def test_a_folder_without_input_type_is_still_an_error(self):
        report = self.check({'match': {'zip': 'Acquisition'}})
        self.assertTrue(any('missing file' in e for e in report.errors))

    def test_a_missing_path_is_still_an_error(self):
        report = self.check({'match': {'zip': 'Nowhere'}, 'input_type': 'fs'})
        self.assertTrue(any('missing file' in e for e in report.errors))


if __name__ == '__main__':
    unittest.main()
