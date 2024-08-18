rem @echo off
setlocal

REM Set the desired Python version
set PYTHON_VERSION=311

REM Path to Python 3.11 installation (adjust if necessary)
set PYTHON_PATH=C:\Program Files\Python%PYTHON_VERSION%
set PYTHON_=%PYTHON_PATH%\python.exe

REM Check if Python 3.11 exists
if not exist "%PYTHON_%" (
    echo Python %PYTHON_% is not installed.
    exit /b 1
)

REM Ensure the Scripts directory of Python 3.11 is added to the system PATH
set PATH=%PYTHON_PATH%\Scripts;%PYTHON_PATH%;%PATH%

REM Navigate to the project directory
cd /d "%~dp0"

REM Activate the virtual environment
call ..\venv\Scripts\activate

REM Add project folders to PYTHONPATH
set PYTHONPATH=%CD%\..\GSMParamLib;%CD%

REM Run the Python script
..\venv\Scripts\python.exe LCFMapper.py

REM Deactivate the virtual environment
call ..\venv\Scripts\deactivate

endlocal
