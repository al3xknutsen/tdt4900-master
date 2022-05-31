@echo off

setlocal

pushd "%~dp0"

set ROOT_DIR=%~dp0
set USD_LIB_DIR=%ROOT_DIR%_build\target-deps\nv_usd\release\lib
set OMNI_CLIENT_DIR=%ROOT_DIR%_build\target-deps\omni_client_library\release
set PYTHON=%ROOT_DIR%_build\target-deps\python\python.exe

set PATH=%PATH%;%USD_LIB_DIR%;%OMNI_CLIENT_DIR%
set PYTHONPATH=%USD_LIB_DIR%\python;%OMNI_CLIENT_DIR%\bindings-python

if not exist "%PYTHON%" (
    echo Python, USD, and Omniverse Client libraries are missing.  Run prebuild.bat to retrieve them.
    popd
    exit /b
)

::The commented lines are for spawning multiple cars
::start "car" "%PYTHON%" source\pyHelloWorld\connector_gnss.py "gnss52_trip3.csv" "car" %*
::start "car2" "%PYTHON%" source\pyHelloWorld\connector_gnss.py "gnss52_trip4.csv" "car2" %*
::start "car3" "%PYTHON%" source\pyHelloWorld\connector_gnss.py "gnss50.csv" "car3" %*
::start "car4" "%PYTHON%" source\pyHelloWorld\connector_gnss.py "gnss52.csv" "car4" %*
::"%PYTHON%" source\pyHelloWorld\connector_gnss.py "gnss52_trip3.csv" "car"
"%PYTHON%" chapter_10_wall_projective/auto_perspective_correction.py

popd