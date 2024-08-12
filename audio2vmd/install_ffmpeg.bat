@echo off
setlocal enabledelayedexpansion

REM -------------- Install FFmpeg --------------------

REM Define the URL for the latest FFmpeg build from a trusted source
set "ffmpeg_url=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

REM Define the download and extraction directories
set "download_dir=%TEMP%\ffmpeg_download"
set "install_dir=%ProgramFiles%\ffmpeg"

REM Create directories
mkdir "%download_dir%" 2>nul
mkdir "%install_dir%" 2>nul

echo Download directory: "%download_dir%"
echo Installation directory: "%install_dir%"

REM Download FFmpeg
echo Downloading FFmpeg...
powershell -Command "(New-Object Net.WebClient).DownloadFile('%ffmpeg_url%', '%download_dir%\ffmpeg.zip')"
if %errorlevel% neq 0 (
    echo Failed to download FFmpeg. Please check your internet connection and try again.
    goto cleanup
)

REM Extract FFmpeg
echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path '%download_dir%\ffmpeg.zip' -DestinationPath '%install_dir%' -Force"
if %errorlevel% neq 0 (
    echo Failed to extract FFmpeg. Please ensure you have sufficient permissions and disk space.
    goto cleanup
)

REM Find the bin directory
set "ffmpeg_bin_dir="
for /d %%i in ("%install_dir%\ffmpeg-*") do (
    if exist "%%i\bin" (
        set "ffmpeg_bin_dir=%%i\bin"
        goto found_bin
    )
)

:found_bin

REM Check if FFmpeg was extracted correctly
if not defined ffmpeg_bin_dir (
    echo Error: FFmpeg bin directory not found. Installation may have failed.
    goto cleanup
)

REM Add FFmpeg to system PATH using PowerShell
echo Adding FFmpeg to system PATH...

REM Define the PowerShell command
set PowerShellCommand=^
$oldPath = [Environment]::GetEnvironmentVariable('Path', 'Machine');^
$newPath = $oldPath + ';%ffmpeg_bin_dir%';^
[Environment]::SetEnvironmentVariable('Path', $newPath, 'Machine');

REM Run the PowerShell command
powershell -Command "%PowerShellCommand%"

echo.
echo FFmpeg installation and PATH setup complete.
echo Please restart your command prompt for the changes to take effect.

:cleanup
echo Cleaning up temporary files...
rmdir /s /q "%download_dir%" 2>nul

exit /b 0