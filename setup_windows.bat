@echo off
setlocal

set "VENV_DIR=.venv"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/5] Creating virtual environment in %VENV_DIR%...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo Failed to create virtual environment.
    exit /b 1
)

echo [2/5] Upgrading pip...
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

echo [3/5] Installing requirements...
call "%VENV_DIR%\Scripts\python.exe" -m pip install ^
    PySide6^>=6.6^,<7.0 ^
    PySide6-Addons^>=6.6^,<7.0 ^
    PyYAML^>=6.0^,<7.0 ^
    numpy^>=1.26^,<3.0 ^
    opencv-python-headless^>=4.9^,<5.0 ^
    torch^>=2.0 ^
    torchvision^>=0.15 ^
    torchaudio^>=2.0
if errorlevel 1 (
    echo Failed to install requirements.
    exit /b 1
)

echo [4/5] Installing ColourSorter package and entry points...
call "%VENV_DIR%\Scripts\python.exe" -m pip install .
if errorlevel 1 (
    echo Failed to install package.
    exit /b 1
)

echo [5/5] Verifying install...
call "%VENV_DIR%\Scripts\coloursorter-bench-cli.exe" --help >nul 2>nul
if errorlevel 1 (
    echo Package installed, but CLI entry point verification failed.
    exit /b 1
)

echo.
echo Setup complete. ColourSorter is installed in %VENV_DIR%.
echo Opening an activated (.venv) command prompt...

start "ColourSorter (.venv)" cmd /k ""%CD%\%VENV_DIR%\Scripts\activate.bat""

endlocal
