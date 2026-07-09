@echo off
setlocal

set JMETER_EXE=apache-jmeter-5.6.3\bin\jmeter.bat
set TEST_FILE=tests\MQTT-Secondary-Broker-Load-Test-(Gromed).jmx
set RESULT_JTL=results\mqtt-results.jtl
set REPORT_DIR=results\mqtt-report

:: Clean up previous results
if exist "%REPORT_DIR%" (
    echo Removing previous report folder...
    rmdir /s /q "%REPORT_DIR%"
)
if exist "%RESULT_JTL%" (
    echo Removing previous result JTL...
    del /q "%RESULT_JTL%"
)

:: Delegate to PowerShell script which handles the HiveMQ thread hang on exit
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0run_mqtt_test.ps1" -Threads 500 -RampUp 120 -Duration 300
endlocal
