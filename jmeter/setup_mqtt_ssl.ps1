# Downloads the broker's self-signed SSL cert and imports it into a JKS truststore
# that JMeter/Paho can use for MQTT over SSL (port 8883).

param(
    [string]$BrokerHost = "135.235.166.209",
    [int]$BrokerPort   = 8883,
    [string]$TrustStore = "C:\jmeter\mqtt-truststore.jks",
    [string]$StorePass  = "changeit",
    [string]$CertFile   = "C:\jmeter\broker-cert.cer",
    [string]$KeytoolExe = "C:\Program Files\Java\jre1.8.0_491\bin\keytool.exe"
)

Write-Host "Connecting to ${BrokerHost}:${BrokerPort} to fetch certificate..."

$tcpClient = New-Object System.Net.Sockets.TcpClient
$tcpClient.Connect($BrokerHost, $BrokerPort)

$sslStream = New-Object System.Net.Security.SslStream(
    $tcpClient.GetStream(),
    $false,
    [System.Net.Security.RemoteCertificateValidationCallback]{ $true }   # accept self-signed
)

try {
    $sslStream.AuthenticateAsClient($BrokerHost)
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($sslStream.RemoteCertificate)
    $certBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    [System.IO.File]::WriteAllBytes($CertFile, $certBytes)
    Write-Host "Certificate saved: $($cert.Subject)"
    Write-Host "  Thumbprint : $($cert.Thumbprint)"
    Write-Host "  Expires    : $($cert.GetExpirationDateString())"
}
finally {
    $sslStream.Close()
    $tcpClient.Close()
}

# Remove existing truststore so keytool doesn't prompt about duplicates
if (Test-Path $TrustStore) {
    Remove-Item $TrustStore -Force
    Write-Host "Removed old truststore."
}

Write-Host "Importing certificate into truststore: $TrustStore"
& $KeytoolExe -import -noprompt `
    -alias "mqtt-broker" `
    -keystore $TrustStore `
    -storepass $StorePass `
    -file $CertFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Truststore created successfully: $TrustStore"
    Write-Host "Run the load test with:  run_mqtt_test.bat"
} else {
    Write-Error "keytool import failed (exit code $LASTEXITCODE)"
    exit 1
}
