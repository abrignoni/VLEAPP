# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vleappGUI.py'],
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
    icon='../icon.icns',
    bundle_identifier='4n6.brigs.VLEAPP',
    version='2.1.0',
)
