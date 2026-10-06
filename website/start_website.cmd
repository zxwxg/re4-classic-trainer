@echo off
rem Serve the RE4 Classic Trainer website locally and open it in the browser.
setlocal
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

echo Starting the website on http://127.0.0.1:8899 ...
start "" http://127.0.0.1:8899/
"%PY%" -m http.server 8899 --bind 127.0.0.1
