@echo off
setlocal

set JMETER_EXE=apache-jmeter-5.6.3\bin\jmeter.bat
set TEST_FILE=tests\MQTT-Steady-State-Load-Test-(Gromed).jmx
set RESULT_JTL=results\mqtt-steady-results.jtl
set REPORT_DIR=results\mqtt-steady-report

:: Clean up previous results
if exist "%REPORT_DIR%" (
    echo Removing previous report folder...
    rmdir /s /q "%REPORT_DIR%"
)
if exist "%RESULT_JTL%" (
    echo Removing previous result JTL...
    del /q "%RESULT_JTL%"
)

:: SSL truststore for self-signed broker cert (created by setup_mqtt_ssl.ps1)
set JVM_ARGS=-Djavax.net.ssl.trustStore=C:\jmeter\mqtt-truststore.jks -Djavax.net.ssl.trustStorePassword=changeit

:: Run JMeter
:: Defaults: 1000 persistent devices, ramped up over 120s, running for 300s,
:: each publishing every 5000ms (matches production's 5s tracking interval).
:: Override with: -JTHREADS=<n> -JRAMP_UP=<sec> -JDURATION=<sec> -JPUBLISH_INTERVAL_MS=<ms>
:: Override broker with: -JTARGET_HOST=<ip> -JTARGET_PORT=<port>
"%JMETER_EXE%" -n -t "%TEST_FILE%" ^
  -JTHREADS=1000 -JRAMP_UP=120 -JDURATION=300 -JPUBLISH_INTERVAL_MS=5000 ^
  -l "%RESULT_JTL%" -e -o "%REPORT_DIR%"

echo.
echo Done. HTML report saved to: %REPORT_DIR%
endlocal
