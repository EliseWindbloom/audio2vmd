echo Installing audio2vmd...

REM Check if Python is installed
python --version 2>NUL
if errorlevel 1 goto errorNoPython

REM Enter audio2vmd folder
cd audio2vmd

REM Create a virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM Install required packages
pip install pydub==0.25.1 PyYAML==6.0.1 tqdm==4.66.4 psutil==6.0.0 spleeter==2.4.0

REM install more compatible version of spleeter over it to avoid errors
pip install spleeter==2.3.2

REM Go back to bat file folder
cd..

echo Installation complete!
echo To use audio2vmd, drag and drop audio to "Audio to VMD" bat file or open for GUI
echo Or alternately, activate the virtual environment with:
echo call audio2vmd\venv\Scripts\activate.bat
echo then run: cd audio2vmd
echo Then run: python audio2vmd.py [options]
pause
exit
