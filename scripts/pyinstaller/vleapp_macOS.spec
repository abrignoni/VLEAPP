# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['../../vleapp.py'],
    pathex=['../scripts/artifacts'],
    binaries=[],
    datas=[
        ('../', 'scripts'),
        ('../../leapp_functions', 'leapp_functions'),
        ('../../assets', 'assets')],
    hiddenimports=[
        # Artifacts are bundled as data files and imported from disk at runtime,
        # so PyInstaller's import-graph analysis never sees what they import.
        # leapp_functions.data_sources
        # is imported only by artifacts, so without this it is missing from the
        # frozen build and every artifact importing it dies at load.
        *collect_submodules('leapp_functions'),
        # Stdlib that only artifacts import; PyInstaller prunes stdlib it cannot
        # see used, so these are absent from the frozen build without this list
        # (the local frozen smoke run died on xml.etree).
        'bz2',
        'gzip',
        'tarfile',
        'xml.etree.ElementTree',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='vleapp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
