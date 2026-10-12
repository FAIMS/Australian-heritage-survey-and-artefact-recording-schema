@echo off
REM ============================================================================
REM Australian Heritage Survey - Project Generator (Windows Launcher)
REM Double-click this file to generate your GeoPackage and QGIS project
REM ============================================================================

title Australian Heritage Survey - Setup Generator
cd /d "%~dp0"

echo ============================================================================
echo   AUSTRALIAN HERITAGE SURVEY & ARTEFACT RECORDING (GeoPackage V0.2)
echo   Project Setup Generator for Windows
echo ============================================================================
echo.

REM Check for Python in PATH or py launcher
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=py -3
    goto RUN
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY_CMD=python
    goto RUN
)

REM If standard Python not in PATH, check QGIS bundled Python (OSGeo4W)
if exist "C:\Program Files\QGIS 3.34\bin\python3.exe" (
    set "PY_CMD=C:\Program Files\QGIS 3.34\bin\python3.exe"
    goto RUN
)
if exist "C:\Program Files\QGIS 3.28\bin\python3.exe" (
    set "PY_CMD=C:\Program Files\QGIS 3.28\bin\python3.exe"
    goto RUN
)
if exist "C:\OSGeo4W\bin\python3.exe" (
    set "PY_CMD=C:\OSGeo4W\bin\python3.exe"
    goto RUN
)

echo [ERROR] Python was not found on your system!
echo.
echo Please do one of the following:
echo   1. Install Python from https://www.python.org/ (check 'Add python.exe to PATH')
echo   2. Or install from the Microsoft Store (search 'Python 3.11' or 'Python 3.12')
echo   3. Or open the 'OSGeo4W Shell' from your QGIS start menu and run this script there.
echo.
pause
exit /b 1

:RUN
echo Using Python: %PY_CMD%
echo.
%PY_CMD% generate_geopackage.py
echo.
echo ============================================================================
echo Setup process finished. Press any key to close this window.
echo ============================================================================
pause >nul
