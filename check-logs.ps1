# Check NGINX RTMP logs in real-time

Write-Host "=== NGINX RTMP Logs ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

docker-compose logs -f rtmp
