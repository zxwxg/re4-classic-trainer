rem Run without elevation - memory features work, file features are disabled.
@echo off
setlocal
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%PY%" -m re4_trainer
pause
