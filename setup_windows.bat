@echo off
setlocal

set "VENV_DIR=.venv"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/3] Creating virtual environment in %VENV_DIR%...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo Failed to create virtual environment.
    exit /b 1
)

echo [2/3] Upgrading pip...
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

echo [3/3] Installing ColourSorter package...
call "%VENV_DIR%\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo Failed to install package.
    exit /b 1
)

echo.
echo Setup complete.
echo Opening an activated (.venv) command prompt...

start "ColourSorter (.venv)" cmd /k ""%CD%\%VENV_DIR%\Scripts\activate.bat""

endlocal
