# for audio2vmd version 13.2+
import subprocess
import sys
from pathlib import Path

# Get the path to the pythonw executable in the virtual environment
venv_pythonw = Path("venv") / "Scripts" / "pythonw.exe"

# Use pythonw to launch the GUI without a console window
subprocess.Popen([str(venv_pythonw), "audio2vmd_gui.py"], creationflags=subprocess.CREATE_NO_WINDOW)
