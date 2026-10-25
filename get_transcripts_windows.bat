@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Fetch YouTube transcripts

set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython

%PY% -c "import sys" >nul 2>&1
if errorlevel 1 goto nopython
%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto oldpython

if not exist ".venv\Scripts\python.exe" (
    echo Setting up the Python environment - this takes a minute the first time...
    %PY% -m venv .venv
    if errorlevel 1 goto venvfail
)

".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet --upgrade -r scripts\requirements.txt
if errorlevel 1 goto pipfail

echo.
echo Downloading transcripts. You can stop at any time - run this file again to continue.
echo.
".venv\Scripts\python.exe" scripts\fetch_transcripts.py %*
if errorlevel 1 goto runfail

echo.
echo Done. The transcripts are in the "transcripts" folder.
echo If any episode is missing, run this file again - it carries on from where it stopped.
pause
exit /b 0

:nopython
echo.
echo Python 3 was not found on this computer.
echo Install it from https://www.python.org/downloads/ and tick
echo "Add python.exe to PATH" during the installation, then run this file again.
pause
exit /b 1

:oldpython
echo.
echo Python is too old. Install Python 3.10 or newer from https://www.python.org/downloads/
pause
exit /b 1

:venvfail
echo.
echo Could not create the Python environment. Try installing Python again from python.org.
pause
exit /b 1

:pipfail
echo.
echo Could not install the required packages. Check your internet connection and try again.
pause
exit /b 1

:runfail
echo.
echo The run ended with an error - see the messages above.
echo The full log is in transcripts\_last_run.log
pause
exit /b 1
