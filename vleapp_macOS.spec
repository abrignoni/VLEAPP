# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['vleapp.py'],
    pathex=['scripts/artifacts'],
    binaries=[],
    datas=[('scripts/', 'scripts')],
    hiddenimports=[
        'blackboxprotobuf',
        'xml.etree.ElementTree',
        'xmltodict',
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
