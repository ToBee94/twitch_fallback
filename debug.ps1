# Debug script for RTMP connection issues (PowerShell)

Write-Host "=== Twitch Stream Manager Debug ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Checking Docker containers..." -ForegroundColor Yellow
docker-compose ps
Write-Host ""

Write-Host "2. Checking if port 1935 is listening..." -ForegroundColor Yellow
netstat -an | findstr "1935"
Write-Host ""

Write-Host "3. Checking NGINX RTMP logs..." -ForegroundColor Yellow
docker-compose logs --tail=50 rtmp
Write-Host ""

Write-Host "4. Checking Windows Firewall for port 1935..." -ForegroundColor Yellow
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*1935*"} | Format-Table -AutoSize
Write-Host ""

Write-Host "5. Testing connectivity to RTMP server..." -ForegroundColor Yellow
Test-NetConnection -ComputerName data.unserioes24.de -Port 1935
Write-Host ""

Write-Host "6. Checking if Docker is running..." -ForegroundColor Yellow
docker info 2>&1 | Select-String "Server Version"
Write-Host ""

Write-Host "=== Debug Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Common solutions:" -ForegroundColor Green
Write-Host "1. Start Docker containers: docker-compose up -d"
Write-Host "2. Open Windows Firewall port 1935:"
Write-Host "   New-NetFirewallRule -DisplayName 'RTMP' -Direction Inbound -LocalPort 1935 -Protocol TCP -Action Allow"
Write-Host "3. Restart Docker: docker-compose restart"
Write-Host "4. Check logs: docker-compose logs -f rtmp"
Write-Host ""
Write-Host "OBS Settings:" -ForegroundColor Yellow
Write-Host "  Server: rtmp://data.unserioes24.de:1935/input"
Write-Host "  Stream Key: obs"
