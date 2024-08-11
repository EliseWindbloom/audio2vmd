@echo off
setlocal enabledelayedexpansion

REM Check if any arguments are passed
if "%~1"=="" goto no_file

REM Get the drive of the batch file
set "batchdrive=%~d0"

REM Change to the directory of the batch file
cd /d "%~dp0"
cd audio2vmd

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Initialize the command with the Python script
set "cmd=python audio2vmd.py"

REM Loop through all arguments and add them to the command
:loop
if "%~1"=="" goto endloop
set "cmd=!cmd! "%~1""
shift
goto loop
:endloop

REM Add the output and model parameters
set "cmd=!cmd! --output "output" --model "Model""

REM Execute the command
%cmd%

REM Deactivate the virtual environment
call deactivate

pause
exit

:no_file
REM Get the drive of the batch file
set "batchdrive=%~d0"

REM Change to the directory of the batch file
cd /d "%~dp0"
cd audio2vmd

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the Python script with a hidden command prompt
python launch_gui.py

REM Run the Python script with a minimized command prompt
REM for minimized instead, use: start /min cmd /c python audio2vmd_gui.py
REM for hidden (less robust way): start /b pythonw audio2vmd_gui.py

exit
