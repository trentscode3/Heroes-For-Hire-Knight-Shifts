# Heroes for Hire: Knight Shifts Demo

This is the public demo build of **Heroes for Hire: Knight Shifts**.

## Demo limits

The demo uses the current game build with this restriction:

- Warrior is playable.
- Robin Hood is not playable.
- Nimbus is not playable.

The demo also stores saves separately from the full game:

```text
%LOCALAPPDATA%\Knight Shifts Demo
```

## Windows install from GitHub

### 1. Install Python

Install Python 3.11 or newer:

```text
https://www.python.org/downloads/
```

During installation, enable:

```text
Add python.exe to PATH
```

### 2. Download the demo

On GitHub:

1. Click the green `Code` button.
2. Click `Download ZIP`.
3. Extract the ZIP.
4. Open the `HeroesForHireKnightShifts_Demo` folder.

### 3. Install pygame

Double-click:

```text
install_windows.bat
```

Or run from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

This creates a local `.venv` folder and installs pygame into it. It does not
install pygame globally.

### 4. Run the demo

Double-click:

```text
run_demo.bat
```

Or run from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

## Manual install commands

If you prefer manual commands:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:KNIGHT_SHIFTS_DEMO = "1"
.\.venv\Scripts\python.exe game_demo.py
```

## Build the Steam demo executable

To create a Windows folder that does not require players to install Python or
pygame:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_steam_demo_windows.ps1
```

The Steam demo output will be:

```text
dist\HeroesForHireKnightShiftsDemo
```

Upload every file in that folder to the Steam demo app depot. Configure the
Steam launch executable as:

```text
HeroesForHireKnightShiftsDemo.exe
```
