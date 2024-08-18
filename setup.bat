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

REM Remove the existing virtual environment if it exists
if exist ..\venv (
    rmdir /s /q ..\venv
)

REM Create a new virtual environment using Python 3.11
"%PYTHON_%" -m venv ..\venv

REM Activate the virtual environment
call ..\venv\Scripts\activate

REM Upgrade pip to the latest version
..\venv\Scripts\python.exe -m pip install --upgrade pip

REM Install required packages for GSMParamLib
..\venv\Scripts\python.exe -m pip install -r ..\GSMParamLib\requirements.txt

REM Install required packages for LCFMapper
..\venv\Scripts\python.exe -m pip install -r requirements.txt

REM Add project folders to PYTHONPATH
set PYTHONPATH=%CD%\..\GSMParamLib;%CD%

REM Deactivate the virtual environment
call ..\venv\Scripts\deactivate

endlocal
