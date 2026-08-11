# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['../../vleappGUI.py'],
    pathex=['../scripts/artifacts'],
    binaries=[],
    datas=[('../', 'scripts'), ('../../assets', 'assets')],
    hiddenimports=[
        # Artifacts are bundled as data files and imported from disk at runtime,
        # so PyInstaller's import-graph analysis never sees what they import.
        # hook-plugin_loader.py was meant to cover this but targets a bare
        # 'plugin_loader' module that no longer exists (it moved to
        # scripts.plugin_loader), so it never fires. leapp_functions.data_sources
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
    [],
    exclude_binaries=True,
    name='vleappGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='vleappGUI',
)

app = BUNDLE(
    coll,
    name='vleappGUI.app',
    icon='../../assets/icon.icns',
    bundle_identifier='4n6.brigs.VLEAPP',
    version='2026.2.0',
)
