param(
    [int]$Threads  = 500,
    [int]$RampUp   = 120,
    [int]$Duration = 300
)

$Root   = $PSScriptRoot
$JMETER = "$Root\apache-jmeter-5.6.3\bin\jmeter.bat"
$TEST   = "$Root\tests\MQTT-Secondary-Broker-Load-Test-(Gromed).jmx"
$JTL    = "$Root\results\mqtt-results.jtl"
$REPORT = "$Root\results\mqtt-report"
$TRUST  = "$Root\mqtt-truststore.jks"

# Cleanup
if (Test-Path $REPORT) { Remove-Item $REPORT -Recurse -Force ; Write-Host "Removed old report." }
if (Test-Path $JTL)    { Remove-Item $JTL    -Force          ; Write-Host "Removed old JTL."    }

# SSL truststore (no quotes needed — path has no spaces)
$env:JVM_ARGS = "-Djavax.net.ssl.trustStore=$TRUST -Djavax.net.ssl.trustStorePassword=changeit"

$jmArgs = "-n -t `"$TEST`" -JTHREADS=$Threads -JRAMP_UP=$RampUp -JDURATION=$Duration -l `"$JTL`" -e -o `"$REPORT`""

Write-Host ""
Write-Host "MQTT Load Test  |  threads=$Threads  ramp=${RampUp}s  duration=${Duration}s"
Write-Host "----------------------------------------------------------------------"

# Write JMeter command to a temp bat to avoid PowerShell/CMD quoting issues
$tempBat = [System.IO.Path]::Combine($env:TEMP, "run_jmeter_mqtt_$PID.bat")
@"
@echo off
set JVM_ARGS=$($env:JVM_ARGS)
"$JMETER" -n -t "$TEST" -JTHREADS=$Threads -JRAMP_UP=$RampUp -JDURATION=$Duration -l "$JTL" -e -o "$REPORT"
exit 0
"@ | Set-Content -Path $tempBat -Encoding ASCII

$maxWaitSec = $RampUp + $Duration + 210
Write-Host "(Auto-kill after $maxWaitSec s if JVM hangs on exit)"
Write-Host ""

# Start via the temp bat — output appears in current console
$proc = Start-Process -FilePath "cmd.exe" `
                      -ArgumentList "/c `"$tempBat`"" `
                      -NoNewWindow -PassThru

$completed = $proc.WaitForExit($maxWaitSec * 1000)

if (-not $completed) {
    Write-Host "`nMax wait exceeded - force-killing JMeter..." -ForegroundColor Yellow
} else {
    Write-Host "`nJMeter process exited. Cleaning up lingering threads..." -ForegroundColor Cyan
}

# Recursively kill the process tree (cmd -> jmeter.bat -> java.exe)
function Stop-Tree ([int]$RootPid) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$RootPid" -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Tree $_.ProcessId }
    Stop-Process -Id $RootPid -Force -ErrorAction SilentlyContinue
}
Stop-Tree $proc.Id
Remove-Item $tempBat -Force -ErrorAction SilentlyContinue

Write-Host ""
if (Test-Path "$REPORT\index.html") {
    Write-Host "Done. HTML report: $REPORT\index.html" -ForegroundColor Green
} else {
    Write-Host "Done. No HTML report found - check JTL: $JTL" -ForegroundColor Yellow
}
