#!/bin/bash
# Debug script for RTMP connection issues

echo "=== Twitch Stream Manager Debug ==="
echo ""

echo "1. Checking Docker containers..."
docker-compose ps
echo ""

echo "2. Checking if port 1935 is listening..."
netstat -an | grep 1935 || ss -tuln | grep 1935
echo ""

echo "3. Checking NGINX RTMP logs..."
docker-compose logs --tail=50 rtmp
echo ""

echo "4. Testing RTMP connection from inside Docker network..."
docker-compose exec stream_manager sh -c "apt-get update && apt-get install -y ffmpeg && ffprobe -v error rtmp://rtmp:1935/input/obs" 2>&1
echo ""

echo "5. Checking firewall status..."
if command -v ufw &> /dev/null; then
    sudo ufw status
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --list-all
fi
echo ""

echo "6. Testing RTMP publish from localhost..."
echo "Attempting to send test stream..."
timeout 5 ffmpeg -re -f lavfi -i testsrc=size=640x480:rate=30 -f lavfi -i sine=frequency=1000 \
    -c:v libx264 -preset ultrafast -b:v 1000k -c:a aac -b:a 128k \
    -f flv rtmp://localhost:1935/input/test 2>&1 | head -20
echo ""

echo "=== Debug Complete ==="
echo ""
echo "Common issues:"
echo "1. Docker containers not running: Run 'docker-compose up -d'"
echo "2. Port 1935 blocked: Check firewall settings"
echo "3. NGINX config error: Check 'docker-compose logs rtmp'"
echo "4. Wrong OBS settings: Server should be rtmp://YOUR_IP:1935/input"
