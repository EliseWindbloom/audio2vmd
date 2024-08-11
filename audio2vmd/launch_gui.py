import subprocess

# This simply lanuches the gui using subprocess (to hopefully be more robust at lanuching)
subprocess.Popen(["pythonw", "audio2vmd_gui.py"], creationflags=subprocess.CREATE_NO_WINDOW)