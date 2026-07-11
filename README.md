# Heroes for Hire: Knight Shifts Demo

This is the public demo build of **Heroes for Hire: Knight Shifts**. To play, follow the instructions below, then in the game folder double click **"game_demo.py"**.

## Demo Limits

- Warrior is playable.
- Robin Hood is not playable.
- Nimbus is not playable.
- Demo saves are stored separately from the full game.

Demo save location:

```text
%LOCALAPPDATA%\Knight Shifts Demo
```

## Download And Run On Windows

### 1. Install Python

Install Python 3.11 or newer from:

```text
https://www.python.org/downloads/
```

During installation, check this box:

```text
Add python.exe to PATH
```

### 2. Download The Demo

1. Open the GitHub page for this repo.
2. Click the green **Code** button.
3. Click **Download ZIP**.
4. Right-click the downloaded ZIP file and choose **Extract All**.
5. Open the extracted folder.

You should see files like:

```text
game_demo.py
install_windows.bat
run_demo.bat
requirements.txt
```

### 3. Install The Demo Requirements

Double-click:

```text
install_windows.bat
```

This creates a local `.venv` folder and installs pygame into it. It does not install pygame globally on your computer.

If double-clicking does not work, open PowerShell in the extracted folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
```

### 4. Start The Demo

Double-click:

```text
run_demo.bat
```

If double-clicking does not work, open PowerShell in the extracted folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

## Manual Install Commands

Use these only if the installer script does not work:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:KNIGHT_SHIFTS_DEMO = "1"
.\.venv\Scripts\python.exe game_demo.py
```

## Build The Steam Demo Executable

To create a Windows folder that does not require players to install Python or pygame:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_steam_demo_windows.ps1
```

The Steam demo output will be:

```text
dist\HeroesForHireKnightShiftsDemo
```

Upload every file in that folder to the Steam demo app depot. Configure the Steam launch executable as:

```text
HeroesForHireKnightShiftsDemo.exe
```
