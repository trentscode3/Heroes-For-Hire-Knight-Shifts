# Steam Windows build

This project can be shipped to Steam without requiring players to install Python
or pygame by packaging the game with PyInstaller. The build output includes the
Python runtime, pygame, game code, assets, fonts, and audio folders.

## Build on Windows

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_steam.ps1
```

The Steam-ready folder will be:

```text
dist\HeroesForHireKnightShifts
```

Upload the contents of that folder with SteamPipe. Configure the Steam launch
option to run:

```text
HeroesForHireKnightShifts.exe
```

## Rebuilding after dependencies are installed

If the build virtual environment already exists and dependencies are installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows_steam.ps1 -SkipInstall
```

## Save data

Save files and preferences are written outside the Steam install folder:

```text
%LOCALAPPDATA%\Knight Shifts
```

This is intentional. Steam users should be able to update, uninstall, or move
the game without deleting save progress.

## Steam release checklist

- Build on a clean Windows machine or VM before uploading.
- Launch `HeroesForHireKnightShifts.exe` directly from the `dist` folder.
- Verify assets, fonts, audio, fullscreen/windowed settings, and saving.
- Upload the whole `dist\HeroesForHireKnightShifts` folder to SteamPipe.
- Test through Steam after upload, not only by double-clicking the executable.
- Add an `.ico` file later and wire it into `HeroesForHireKnightShifts.spec`
  before final public release.
