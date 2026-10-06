@echo off
rem Build a single-file RE4ClassicTrainer.exe (icon + version info, asks for admin on launch).
setlocal
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul || set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

"%PY%" -m pip install --quiet --upgrade pyinstaller || goto :err
"%PY%" "%~dp0packaging\make_icon.py" || goto :err
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin ^
  --name "RE4ClassicTrainer" ^
  --collect-all customtkinter ^
  --icon "%~dp0packaging\icon.ico" ^
  --version-file "%~dp0packaging\version_info.txt" ^
  --add-data "%~dp0packaging\dule_avatar.png;packaging" ^
  --add-data "%~dp0packaging\dule_brand.png;packaging" ^
  --add-data "%~dp0packaging\icon_umbrella.png;packaging" ^
  --add-data "%~dp0packaging\steam_avatar.png;packaging" ^
  --add-data "%~dp0packaging\icon.ico;packaging" ^
  --workpath "%TEMP%\re4trainer_build" ^
  --specpath "%TEMP%\re4trainer_build" ^
  "%~dp0trainer_launcher.py" || goto :err

echo.
echo Built: dist\RE4ClassicTrainer.exe
pause
goto :eof

:err
echo Build failed.
pause
