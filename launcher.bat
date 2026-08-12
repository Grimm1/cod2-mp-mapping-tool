@echo off
setlocal

echo -----------------------------------------
echo Checking for Python installation...
echo -----------------------------------------

python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo Python is NOT installed or not in PATH.
    echo Install Python from the Microsoft Store:
    echo   https://apps.microsoft.com/detail/9PJPW5LDXLZ5
    echo.
    echo Make sure to enable "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo Python detected.
python --version

echo -----------------------------------------
echo Checking for pip...
echo -----------------------------------------

python -m pip --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo pip is missing. Bootstrapping pip...
    python -m ensurepip --default-pip
)

echo pip detected.
python -m pip --version

echo -----------------------------------------
echo Checking for PyQt6 installation...
echo -----------------------------------------

python -m pip show PyQt6 >nul 2>&1
IF ERRORLEVEL 1 (
    echo PyQt6 is not installed

    echo SECURITY NOTICE:
    echo Installing Python packages from the internet can be risky
    echo Only proceed if you trust the source (PyPI)

    echo Installing PyQt6...
    python -m pip install --upgrade pip
    python -m pip install PyQt6
) ELSE (
    echo PyQt6 is already installed
)

python -m pip show psutil >nul 2>&1
IF ERRORLEVEL 1 (
    echo psutil is not installed
    echo Installing psutil...
    python -m pip install psutil
) ELSE (
    echo psutil is already installed
)

echo -----------------------------------------
echo Running main.py...
echo -----------------------------------------

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%main.py"

echo -----------------------------------------
echo Finished.
echo -----------------------------------------
pause
