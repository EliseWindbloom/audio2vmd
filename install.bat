@echo off
setlocal enabledelayedexpansion

echo Installing audio2vmd...

REM Check if Python 3.10.6 is directly accessible
for %%p in (python python3) do (
    for /f "tokens=*" %%i in ('%%p --version 2^>^&1') do set PYTHON_VERSION=%%i
    if "!PYTHON_VERSION!"=="Python 3.10.6" (
        echo Found Python 3.10.6 using %%p
        set PYTHON_CMD=%%p
        goto :found_python
    )
)

REM Search for Python 3.10.6 in PATH
for %%p in (python.exe python3.exe) do (
    for %%i in (%%p) do (
        set "PYTHON_PATH=%%~$PATH:i"
        if not "!PYTHON_PATH!"=="" (
            for /f "tokens=*" %%j in ('""!PYTHON_PATH!" --version" 2^>^&1') do set PYTHON_VERSION=%%j
            if "!PYTHON_VERSION!"=="Python 3.10.6" (
                echo Found Python 3.10.6 at !PYTHON_PATH!
                set PYTHON_CMD=!PYTHON_PATH!
                goto :found_python
            )
        )
    )
)

REM If not found, search common installation directories
for %%d in ("%ProgramFiles%\Python310" "%ProgramFiles(x86)%\Python310" "%LocalAppData%\Programs\Python\Python310" "C:\Python310") do (
    for %%p in (python.exe python3.exe) do (
        if exist "%%~d\%%p" (
            for /f "tokens=*" %%j in ('"%%~d\%%p" --version 2^>^&1') do set PYTHON_VERSION=%%j
            if "!PYTHON_VERSION!"=="Python 3.10.6" (
                echo Found Python 3.10.6 at %%~d\%%p
                set PYTHON_CMD=%%~d\%%p
                goto :found_python
            )
        )
    )
)

echo Python 3.10.6 not found. Please ensure it is installed and added to PATH.
pause
exit /b 1

:found_python
REM Enter audio2vmd folder
cd audio2vmd

REM Create a virtual environment
"%PYTHON_CMD%" -m venv venv
call venv\Scripts\activate.bat

REM Install required packages
pip install pydub==0.25.1 PyYAML==6.0.1 tqdm==4.66.4 psutil==6.0.0 spleeter==2.4.0

REM install more compatible version of spleeter over it to avoid errors
pip install spleeter==2.3.2

REM install numpy again in case of errors
pip install numpy==1.22.4

REM Generate a list of installed packages
pip list > installed_list.txt

REM Go back to bat file folder
cd..

echo Installation complete!
echo To use audio2vmd, drag and drop audio to "Audio to VMD" bat file or open for GUI
echo Or alternately, activate the virtual environment with:
echo call audio2vmd\venv\Scripts\activate.bat
echo then run: cd audio2vmd
echo Then run: python audio2vmd.py [options]
pause
exit /b 0
