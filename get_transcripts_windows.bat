@echo off
REM Double-click to download all transcripts on your own computer (needs Python 3.10+ from python.org).
cd /d "%~dp0"
python -m pip install --upgrade -r scripts\requirements.txt || goto :error
python scripts\fetch_transcripts.py || goto :error
echo.
echo Done. Transcripts are in the "transcripts" folder.
pause
exit /b 0
:error
echo.
echo Something failed. Make sure Python is installed and "Add python.exe to PATH" was ticked.
pause
exit /b 1
