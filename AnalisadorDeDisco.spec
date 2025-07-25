# -*- mode: python ; coding: utf-8 -*-

# Define os ficheiros de dados para incluir
data_files = [
    ('Arial.ttf', '.'),
    ('app_icon.ico', '.'), # <-- VÍRGULA ADICIONADA
    ('splash_screen.png', '.')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=['numpy', 'pandas._libs.tslibs.nattype'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AnalisadorDeDisco',
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
    icon='app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AnalisadorDeDisco'
)