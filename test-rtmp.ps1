# Test RTMP server with known-working config

Write-Host "=== Testing RTMP Server ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Stopping current containers..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "Step 2: Backing up current config..." -ForegroundColor Yellow
Copy-Item nginx.conf nginx.conf.backup -Force
Write-Host "Backup saved to nginx.conf.backup"

Write-Host ""
Write-Host "Step 3: Using known-working config..." -ForegroundColor Yellow
Copy-Item nginx-working.conf nginx.conf -Force

Write-Host ""
Write-Host "Step 4: Starting containers with fresh config..." -ForegroundColor Yellow
docker-compose up -d --force-recreate

Write-Host ""
Write-Host "Step 5: Waiting 5 seconds for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Step 6: Checking if RTMP is running..." -ForegroundColor Yellow
docker-compose logs rtmp | Select-String -Pattern "nginx" -Context 2,0

Write-Host ""
Write-Host "=== TEST WITH OBS NOW ===" -ForegroundColor Green
Write-Host ""
Write-Host "OBS Settings:" -ForegroundColor Cyan
Write-Host "  Server: rtmp://data.unserioes24.de:1935/input"
Write-Host "  Stream Key: test"
Write-Host ""
Write-Host "After testing, watch logs with:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f rtmp"
Write-Host ""
Write-Host "To restore original config:" -ForegroundColor Yellow
Write-Host "  Copy-Item nginx.conf.backup nginx.conf -Force"
Write-Host "  docker-compose restart rtmp"
