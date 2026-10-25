@echo off
REM Double-click to download all transcripts on your own computer (needs Python 3.10+ from python.org).
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (set PY=python) else (set PY=py -3)
%PY% -m pip install --upgrade -r scripts\requirements.txt || goto :error
%PY% scripts\fetch_transcripts.py || goto :error
echo.
echo Done. Transcripts are in the "transcripts" folder.
pause
exit /b 0
:error
echo.
echo Something failed. Make sure Python is installed and "Add python.exe to PATH" was ticked.
pause
exit /b 1
