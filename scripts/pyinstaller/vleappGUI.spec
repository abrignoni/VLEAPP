# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['..\\..\\vleappGUI.py'],
    pathex=['..\\scripts\\artifacts'],
    binaries=[],
    datas=[('..\\', '.\\scripts'), ('..\\..\\assets', '.\\assets')],
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
    hookspath=['.\\'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='vleappGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    hide_console='hide-early',
    disable_windowed_traceback=False,
    upx_exclude=[],
    version='vleapp-file_version_info.txt',
    runtime_tmpdir=None )
