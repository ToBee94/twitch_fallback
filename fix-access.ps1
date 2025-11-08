# Quick fix for "access forbidden by rule" error

Write-Host "=== Fixing NGINX Access Rules ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Checking current config in container..." -ForegroundColor Yellow
docker exec twitch_rtmp_server cat /etc/nginx/nginx.conf | Select-String -Pattern "allow publish" -Context 1,1

Write-Host ""
Write-Host "Step 2: Stopping container..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "Step 3: Ensuring nginx-working.conf is used..." -ForegroundColor Yellow
Copy-Item nginx-working.conf nginx.conf -Force
Write-Host "Config replaced with nginx-working.conf"

Write-Host ""
Write-Host "Step 4: Recreating container with new config..." -ForegroundColor Yellow
docker-compose up -d --force-recreate

Write-Host ""
Write-Host "Step 5: Waiting for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Step 6: Verifying new config in container..." -ForegroundColor Yellow
docker exec twitch_rtmp_server cat /etc/nginx/nginx.conf | Select-String -Pattern "allow publish" -Context 1,1

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host ""
Write-Host "You should see: 'allow publish all;'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Now try streaming from OBS!" -ForegroundColor Green
Write-Host "Watch logs with: docker-compose logs -f rtmp"
