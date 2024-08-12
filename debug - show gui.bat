@echo off
setlocal enabledelayedexpansion

REM Get the drive of the batch file
set "batchdrive=%~d0"

REM Change to the directory of the batch file
cd /d "%~dp0"
cd audio2vmd

REM Activate the virtual environment
call venv\Scripts\activate.bat

echo ==please share any errors that appear in this command line window==
REM Run the Python script with a hidden command prompt
python audio2vmd_gui.py

pause
