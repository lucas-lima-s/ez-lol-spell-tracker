@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BOOTSTRAP="
call :probe "py -3.14"
call :probe "py -3.13"
call :probe "python"
call :probe_path "C:\Python314\python.exe"
call :probe_path "C:\Python313\python.exe"
call :probe_path "%LocalAppData%\Programs\Python\Python314\python.exe"
call :probe_path "%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined BOOTSTRAP (
    echo [ERROR] No Python 3.13+ found on this machine.
    echo Install it from https://www.python.org/downloads/
    echo or set "pythonPath" in configs.json to a valid python.exe.
    pause
    exit /b 1
)

set "TARGET_PY="
for /f "usebackq delims=" %%i in (`%BOOTSTRAP% scripts\bootstrap.py`) do set "TARGET_PY=%%i"
if not defined TARGET_PY (
    echo [ERROR] Bootstrap failed. See the message above.
    pause
    exit /b 1
)

if not exist "lib\PyInstaller" (
    echo [ERROR] lib\ missing PyInstaller. Run build_environment.bat first.
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0lib"

if exist "dist\EzSpellTracker" rmdir /s /q "dist\EzSpellTracker"

"%TARGET_PY%" -m PyInstaller --noconfirm --clean --onedir --noconsole ^
    --name EzSpellTracker ^
    --paths "%~dp0." --paths "%~dp0lib" ^
    --specpath "%~dp0build" --workpath "%~dp0build" --distpath "%~dp0dist" ^
    "%~dp0src\main.py"
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

xcopy /e /i /y "%~dp0assets" "%~dp0dist\EzSpellTracker\assets" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy assets into the dist folder.
    pause
    exit /b 1
)

echo.
echo Release ready at "%~dp0dist\EzSpellTracker".
pause
exit /b 0

:probe
if defined BOOTSTRAP goto :eof
%~1 -c "import sys; sys.exit(0 if sys.version_info >= (3,13) and 'free-threading' not in sys.version else 1)" >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP=%~1"
goto :eof

:probe_path
if defined BOOTSTRAP goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3,13) and 'free-threading' not in sys.version else 1)" >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP=%~s1"
goto :eof
