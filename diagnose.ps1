# Complete diagnosis script

Write-Host "=== Step 1: Checking if containers are running ===" -ForegroundColor Cyan
docker-compose ps
Write-Host ""

Write-Host "=== Step 2: Checking current nginx.conf in container ===" -ForegroundColor Cyan
docker exec twitch_rtmp_server cat /etc/nginx/nginx.conf | Select-String -Pattern "chunk_size|timeout|buflen" -Context 0,1
Write-Host ""

Write-Host "=== Step 3: Last 30 lines of NGINX logs ===" -ForegroundColor Cyan
docker-compose logs --tail=30 rtmp
Write-Host ""

Write-Host "=== Step 4: Checking if port 1935 is listening ===" -ForegroundColor Cyan
netstat -an | findstr "1935"
Write-Host ""

Write-Host "=== Step 5: Testing connection from host ===" -ForegroundColor Cyan
Test-NetConnection -ComputerName localhost -Port 1935
Write-Host ""

Write-Host "=== Step 6: Container restart times ===" -ForegroundColor Cyan
docker ps --filter "name=twitch_rtmp" --format "table {{.Names}}\t{{.Status}}"
Write-Host ""

Write-Host "=== RECOMMENDATION ===" -ForegroundColor Yellow
Write-Host "If chunk_size is not 8192, run:"
Write-Host "  docker-compose down"
Write-Host "  docker-compose up -d --force-recreate"
Write-Host ""
Write-Host "Then try streaming again and run:"
Write-Host "  docker-compose logs -f rtmp"
