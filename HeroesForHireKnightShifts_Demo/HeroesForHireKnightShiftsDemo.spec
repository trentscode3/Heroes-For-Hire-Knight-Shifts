# Run with:
#   pyinstaller --clean --noconfirm HeroesForHireKnightShiftsDemo.spec

from pathlib import Path


project_root = Path.cwd()


a = Analysis(
    ["game_demo.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets"), "assets"),
    ],
    hiddenimports=[],
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
    name="HeroesForHireKnightShiftsDemo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HeroesForHireKnightShiftsDemo",
)
