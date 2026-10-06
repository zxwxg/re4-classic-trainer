@echo off
rem Launch the trainer with administrator rights (needed to write game/save files).
setlocal
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" if "%PY%"=="py" goto :nopython

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -Verb RunAs -WorkingDirectory '%~dp0' -FilePath '%PY%' -ArgumentList '-m','re4_trainer'"
goto :eof

:nopython
echo Could not find Python. Install it from https://www.python.org/downloads/ or build the exe with build_exe.bat.
pause
