# Troubleshooting Guide

## OBS Connection Issues: "Connection Lost"

If OBS cannot connect to the RTMP server, follow these steps:

### 1. Check if Docker is Running

```bash
docker-compose ps
```

Both `twitch_rtmp_server` and `twitch_stream_manager` should be "Up".

If not running:
```bash
docker-compose up -d
```

### 2. Check NGINX Logs

```bash
docker-compose logs -f rtmp
```

Look for error messages or connection attempts.

### 3. Test Port Accessibility

**From the same machine:**
```bash
telnet localhost 1935
```

**From another machine:**
```bash
telnet data.unserioes24.de 1935
```

If connection fails, check firewall settings.

### 4. Open Firewall Port

**Linux (Ubuntu/Debian):**
```bash
sudo ufw allow 1935/tcp
sudo ufw reload
```

**Linux (CentOS/RHEL):**
```bash
sudo firewall-cmd --permanent --add-port=1935/tcp
sudo firewall-cmd --reload
```

**Windows:**
```powershell
New-NetFirewallRule -DisplayName "RTMP Server" -Direction Inbound -LocalPort 1935 -Protocol TCP -Action Allow
```

### 5. Verify NGINX Configuration

The NGINX config must allow publishing from your OBS IP address.

Check current config:
```bash
cat nginx.conf
```

For the `input` application, you should see:
```nginx
allow publish all;
```

If you see `deny publish all;`, OBS connections will be blocked!

### 6. Restart Containers After Config Changes

```bash
docker-compose restart rtmp
```

### 7. Test with FFmpeg

Test if the RTMP server accepts streams:

```bash
ffmpeg -re -f lavfi -i testsrc=size=640x480:rate=30 \
  -f lavfi -i sine=frequency=1000 \
  -c:v libx264 -preset ultrafast -b:v 1000k \
  -c:a aac -b:a 128k \
  -f flv rtmp://data.unserioes24.de:1935/input/test
```

Press Ctrl+C to stop after a few seconds. Check logs:
```bash
docker-compose logs rtmp | tail -20
```

### 8. Check Docker Network

Verify the RTMP container can be reached:

```bash
docker network inspect twitch_fallback_twitch_network
```

### 9. Common OBS Settings Issues

**Correct Settings:**
- Service: `Custom`
- Server: `rtmp://data.unserioes24.de:1935/input`
- Stream Key: `obs`

**Common Mistakes:**
- ❌ Including stream key in server URL
- ❌ Using wrong port (e.g., 1936 instead of 1935)
- ❌ Missing `/input` path
- ❌ Using `https://` or `http://` instead of `rtmp://`

### 10. Debug Mode

Enable verbose NGINX logging:

Edit `nginx.conf` and add at the top:
```nginx
error_log /var/log/nginx/error.log debug;
```

Restart and check logs:
```bash
docker-compose restart rtmp
docker-compose logs -f rtmp
```

## Port Already in Use

If you get "port 1935 already in use":

**Check what's using the port:**
```bash
# Linux/Mac
sudo lsof -i :1935

# Windows
netstat -ano | findstr :1935
```

**Stop the conflicting service or change the port in docker-compose.yml:**
```yaml
ports:
  - "1936:1935"  # Use different external port
```

Then update OBS server to `rtmp://data.unserioes24.de:1936/input`

## Stream Drops or Stutters

1. **Reduce bitrate in OBS**
   - Video: 2000 kbps or lower
   - Audio: 128 kbps

2. **Check upload speed**
   ```bash
   # Test your upload speed
   speedtest-cli
   ```

3. **Enable CBR in OBS**
   - Settings → Output → Rate Control: CBR

4. **Increase keyframe interval**
   - Settings → Output → Keyframe Interval: 2 seconds

## Authentication Issues (If using nginx-secure.conf)

If you want to secure your RTMP server with authentication:

1. Use `nginx-secure.conf` instead of `nginx.conf`
2. Implement authentication in Flask app
3. Use stream keys that are validated

## Still Having Issues?

Run the debug script:

**Linux/Mac:**
```bash
chmod +x debug.sh
./debug.sh
```

**Windows PowerShell:**
```powershell
.\debug.ps1
```

This will check all common issues and provide a detailed report.

## Getting Help

When asking for help, please provide:
1. Output of `docker-compose ps`
2. Output of `docker-compose logs rtmp`
3. OBS log file (Help → Log Files → Upload Current Log)
4. Your OS and Docker version
5. Whether OBS is on the same machine or remote

## Security Note

The default configuration allows RTMP publishing from anywhere (`allow publish all`).

For production, consider:
1. Restricting to specific IP addresses
2. Using stream key authentication
3. Setting up a VPN
4. Using nginx-secure.conf with authentication
