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

if not exist "lib\PySide6" (
    echo [ERROR] lib\ missing or incomplete. Run build_environment.bat first.
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0lib"
"%TARGET_PY%" -m src.main
if %errorlevel% neq 0 pause
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
