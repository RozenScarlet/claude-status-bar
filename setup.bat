@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Claude Status Bar Setup Tool v2.0
echo ========================================
echo.

REM Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.6+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python installed
echo.

REM Install dependencies
echo [2/5] Installing dependencies...
python -m pip install --quiet requests urllib3 2>nul
if errorlevel 1 (
    echo [WARNING] Dependency installation may have failed
) else (
    echo [OK] Dependencies installed
)
echo.

REM Get API Key
echo [3/5] Configure Cubence API Key...
echo.
echo Please enter your Cubence API Key:
echo (Get it from https://cubence.com)
echo.
set /p API_KEY="API Key: "
if "!API_KEY!"=="" (
    echo [ERROR] API Key cannot be empty
    pause
    exit /b 1
)
echo [OK] API Key configured
echo.

REM Locate .claude folder
echo [4/5] Configuring Claude Code...
set CLAUDE_DIR=%USERPROFILE%\.claude
if not exist "!CLAUDE_DIR!" (
    echo [ERROR] .claude folder not found: !CLAUDE_DIR!
    echo Please ensure Claude Code is installed
    pause
    exit /b 1
)
echo [OK] Found .claude folder: !CLAUDE_DIR!

REM Backup settings.json
set SETTINGS_FILE=!CLAUDE_DIR!\settings.json
if exist "!SETTINGS_FILE!" (
    echo [*] Backing up settings...
    copy "!SETTINGS_FILE!" "!SETTINGS_FILE!.backup" >nul 2>&1
    echo [OK] Backup created
)

REM Copy files
echo [*] Copying files...
set SCRIPT_DIR=%~dp0
copy "!SCRIPT_DIR!status-final.py" "!CLAUDE_DIR!\status-final.py" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy status-final.py
    pause
    exit /b 1
)
copy "!SCRIPT_DIR!run-status.bat" "!CLAUDE_DIR!\run-status.bat" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy run-status.bat
    pause
    exit /b 1
)
echo [OK] Files copied
echo.

REM Replace API Key - create temp Python script
echo [*] Configuring API Key...
set STATUS_PY=!CLAUDE_DIR!\status-final.py

echo import sys > temp_replace.py
echo import re >> temp_replace.py
echo file_path = sys.argv[1] >> temp_replace.py
echo api_key = sys.argv[2] >> temp_replace.py
echo with open(file_path, 'r', encoding='utf-8'^) as f: >> temp_replace.py
echo     content = f.read(^) >> temp_replace.py
echo pattern = r'CUBENCE_API_KEY\s*=\s*[\"'"'"'].*?[\"'"'"']' >> temp_replace.py
echo replacement = 'CUBENCE_API_KEY = "' + api_key + '"' >> temp_replace.py
echo content = re.sub(pattern, replacement, content^) >> temp_replace.py
echo with open(file_path, 'w', encoding='utf-8'^) as f: >> temp_replace.py
echo     f.write(content^) >> temp_replace.py

python temp_replace.py "!STATUS_PY!" "!API_KEY!"
if errorlevel 1 (
    echo [ERROR] Failed to configure API Key
    del temp_replace.py
    pause
    exit /b 1
)
del temp_replace.py
echo [OK] API Key configured
echo.

REM Update settings.json - create temp Python script
echo [*] Updating Claude Code settings...

echo import json > temp_settings.py
echo import sys >> temp_settings.py
echo import os >> temp_settings.py
echo settings_file = sys.argv[1] >> temp_settings.py
echo bat_file = sys.argv[2] >> temp_settings.py
echo config = {} >> temp_settings.py
echo if os.path.exists(settings_file^): >> temp_settings.py
echo     try: >> temp_settings.py
echo         with open(settings_file, 'r', encoding='utf-8'^) as f: >> temp_settings.py
echo             config = json.load(f^) >> temp_settings.py
echo     except: >> temp_settings.py
echo         pass >> temp_settings.py
echo config['statusLine'] = {'type': 'command', 'command': bat_file} >> temp_settings.py
echo with open(settings_file, 'w', encoding='utf-8'^) as f: >> temp_settings.py
echo     json.dump(config, f, indent=2, ensure_ascii=False^) >> temp_settings.py

python temp_settings.py "!SETTINGS_FILE!" "!CLAUDE_DIR!\run-status.bat"
if errorlevel 1 (
    echo [ERROR] Failed to update settings.json
    del temp_settings.py
    pause
    exit /b 1
)
del temp_settings.py
echo [OK] Settings updated
echo.

REM Test
echo [5/5] Testing status bar...
echo.
echo ----------------------------------------
call "!CLAUDE_DIR!\run-status.bat"
echo ----------------------------------------
echo.

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Configuration:
echo   - API Key: !API_KEY:~0,20!...
echo   - Status script: !CLAUDE_DIR!\status-final.py
echo   - Launch script: !CLAUDE_DIR!\run-status.bat
echo   - Settings file: !SETTINGS_FILE!
echo.
echo Please restart Claude Code to see the status bar
echo.
pause
