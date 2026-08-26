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

if exist "lib" rmdir /s /q "lib"
if exist "lib" (
    echo [ERROR] Could not remove the existing lib\ directory.
    echo Close any running instance of the app and try again.
    pause
    exit /b 1
)

"%TARGET_PY%" -m pip --version >nul 2>nul
if errorlevel 1 "%TARGET_PY%" -m ensurepip --upgrade

"%TARGET_PY%" -m pip install --upgrade --target "%~dp0lib" -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Dependencies installed into lib\ using "%TARGET_PY%".
echo All done!
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
