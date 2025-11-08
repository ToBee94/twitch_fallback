# Quick Fix: OBS Connection Error 10053

## Error Symptoms
```
Connection to rtmp://... successful
WriteN, RTMP send error 10053 (19 bytes)
WriteN, RTMP send error 10038 (35 bytes)
```

This means OBS connects but NGINX immediately closes the connection.

## Fix Steps (Choose ONE method)

### Method 1: Use Updated Config (RECOMMENDED)

1. **Stop containers:**
```bash
docker-compose down
```

2. **Restart with new config:**
```bash
docker-compose up -d
```

3. **Check logs:**
```bash
docker-compose logs -f rtmp
```

4. **Try streaming from OBS**

### Method 2: Use Minimal Config (DEBUGGING)

If Method 1 doesn't work, test with minimal config:

1. **Backup current config:**
```bash
cp nginx.conf nginx.conf.backup
```

2. **Use minimal config:**
```bash
cp nginx-minimal.conf nginx.conf
```

3. **Restart:**
```bash
docker-compose restart rtmp
```

4. **Test streaming from OBS**

5. **If working, restore and investigate:**
```bash
cp nginx.conf.backup nginx.conf
docker-compose restart rtmp
```

### Method 3: Use Host Network Mode

Docker's bridge networking can cause issues. Try host mode:

1. **Stop containers:**
```bash
docker-compose down
```

2. **Use host network compose file:**
```bash
docker-compose -f docker-compose-host-network.yml up -d
```

3. **Test streaming**

**Note:** Host mode only works on Linux. On Windows/Mac, skip to Method 4.

### Method 4: Direct NGINX Container (TESTING ONLY)

Test if NGINX RTMP works at all:

```bash
# Run standalone NGINX RTMP
docker run -d --name test-rtmp -p 1935:1935 tiangolo/nginx-rtmp

# Test with FFmpeg
ffmpeg -re -f lavfi -i testsrc=size=640x480:rate=30 \
  -f lavfi -i sine=frequency=1000 \
  -c:v libx264 -preset ultrafast -b:v 1000k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost:1935/live/test

# Clean up
docker stop test-rtmp
docker rm test-rtmp
```

If this works, the issue is with your nginx.conf.

## Common Causes & Solutions

### 1. Stream Key Mismatch
**Symptom:** Connection closes immediately

**Check OBS settings:**
- Server: `rtmp://data.unserioes24.de:1935/input`
- Stream Key: `obs` (must match what NGINX expects)

### 2. Firewall Blocking
**Symptom:** Connection established then drops

**Check firewall:**
```bash
# Windows
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*1935*"}

# Linux
sudo ufw status | grep 1935
```

**Open port:**
```bash
# Windows
New-NetFirewallRule -DisplayName "RTMP" -Direction Inbound -LocalPort 1935 -Protocol TCP -Action Allow

# Linux
sudo ufw allow 1935/tcp
```

### 3. MTU/MSS Issues
**Symptom:** Connection works briefly then fails

**OBS Settings:**
- Settings → Advanced → Network
- Set "Bind to IP": Automatic
- Try enabling/disabling "Dynamic Bitrate"

### 4. Chunk Size Too Small
**Symptom:** WriteN errors

**Already fixed in updated nginx.conf:**
```nginx
chunk_size 8192;  # Increased from 4096
```

### 5. Reverse Proxy / NAT Issues
**Symptom:** Works locally but not remotely

**Check if you're behind NAT:**
```bash
# Test from inside
curl -v telnet://localhost:1935

# Test from outside
curl -v telnet://data.unserioes24.de:1935
```

**Solutions:**
- Port forward 1935 in router
- Use DMZ or bridge mode
- Try host network mode (Linux only)

## Verification Commands

### 1. Check if NGINX is listening:
```bash
docker exec twitch_rtmp_server netstat -tuln | grep 1935
```

### 2. Check NGINX logs:
```bash
docker-compose logs --tail=100 rtmp
```

### 3. Test connection from Docker host:
```bash
telnet localhost 1935
```

### 4. Test connection from outside:
```bash
telnet data.unserioes24.de 1935
```

### 5. Watch live stats:
```bash
curl http://localhost:8080/stat
```

## Still Not Working?

### Enable Debug Logging

1. **Add to nginx.conf (top level):**
```nginx
error_log /var/log/nginx/error.log debug;
```

2. **Restart:**
```bash
docker-compose restart rtmp
```

3. **Try streaming and capture logs:**
```bash
docker-compose logs rtmp > debug-log.txt
```

4. **Share the log for analysis**

### Alternative: Use SRT Instead

If RTMP continues to fail, consider using SRT protocol:
- More reliable over unstable connections
- Built-in error correction
- Better for internet streaming

Let me know if you want SRT setup instructions.

## Success Indicators

You know it's working when:
1. OBS shows "green" status
2. `docker-compose logs rtmp` shows "Publishing" messages
3. `curl http://localhost:8080/stat` shows active streams
4. Stream Manager detects the input stream

## Next Steps After Fix

Once streaming works:
1. Optimize OBS encoder settings
2. Set up fallback media
3. Configure Twitch credentials
4. Test stream switching
5. Secure with authentication (nginx-secure.conf)
