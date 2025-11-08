# Twitch Stream Manager with Fallback

A professional stream manager that forwards RTMP streams from OBS to Twitch and automatically plays a fallback image or video during interruptions.

## Features

- 🎥 **OBS to Twitch**: Seamlessly forwards RTMP streams from OBS to Twitch
- 🔄 **Automatic Fallback**: Switches to fallback media (image or video) on stream interruption
- 🎵 **Multi-Audio Tracks**: Separate audio tracks for Stream and VOD (Twitch Partner)
- 🌐 **Web Interface**: User-friendly browser-based configuration
- 📁 **Media Gallery**: Upload and manage fallback images and videos
- 🔒 **Authentication**: Login protection for web UI (planned)
- 🔑 **Token Protection**: RTMP stream protection with tokens (planned)
- 🚀 **Seamless Streaming**: No interruptions on Twitch through local RTMP buffer
- 🐳 **Docker**: Easy deployment with Docker Compose

## Architecture

The application uses a 2-stage approach for seamless streaming:

1. **OBS** → **Local RTMP Server** (input app)
2. **Stream Manager** reads from **Local RTMP Server** or uses **Fallback** → **Twitch**

When switching between OBS stream and fallback, only the input source is changed while the output to Twitch continues uninterrupted.

## Prerequisites

- Docker and Docker Compose
- Twitch account with Stream Key
- OBS Studio (or other RTMP-capable streaming software)

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd twitch_fallback
```

### 2. Prepare Configuration

Create a `config.yml` file (see `config.example.yml`):

```yaml
rtmp_input_url: 'rtmp://rtmp:1935/input/obs'
twitch_rtmp_url: 'rtmp://live.twitch.tv/app'
twitch_stream_key: 'YOUR_TWITCH_STREAM_KEY'
fallback_type: 'image'  # 'image' or 'video'
fallback_image: 'media/fallback.jpg'
fallback_video: 'media/fallback.mp4'
rtmp_timeout: 5
check_interval: 2
video_bitrate: '2500k'
audio_bitrate: '160k'
fps: 30
resolution: '1920x1080'
```

### 3. Provide Fallback Media

Place a fallback image or video in the `media/` folder:

```bash
# Example: Fallback image
cp your-fallback-image.jpg media/fallback.jpg

# Or: Fallback video
cp your-fallback-video.mp4 media/fallback.mp4
```

### 4. Start Docker Containers

```bash
docker-compose up -d
```

The web UI is now accessible at `http://localhost:5000`.

## Usage

### Web Interface

1. Open `http://localhost:5000` in your browser
2. Navigate to **Configuration** and enter your settings
3. Go to **Media** to upload fallback images/videos
4. Start the stream in the **Dashboard**

### Configure OBS

Configure OBS to stream to the local RTMP server:

1. **Open OBS Studio**
2. **Go to Settings → Stream**
3. **Select "Custom" as Service**
4. **Server:** `rtmp://localhost:1935/input`
5. **Stream Key:** `obs`
6. **Click "OK" and "Start Streaming"**

**For Docker (if OBS runs on a different machine):**
- Replace `localhost` with the IP address of the Docker host
- Ensure port 1935 is accessible from outside

### Recommended Twitch Settings

| Quality | Resolution | FPS | Video Bitrate | Audio Bitrate | Audio Tracks |
|---------|------------|-----|---------------|---------------|--------------|
| Low | 854x480 | 30 | 1000k | 128k | 1 |
| Medium | 1280x720 | 30 | 2500k | 160k | 1 |
| High (Partner) | 1920x1080 | 60 | 6000k | 160k | 1-3 |

**Note:** Twitch limits the maximum bitrate to approximately 6000 kbit/s. For non-partners, 2500-4500 kbit/s is recommended.

### Multi-Audio Tracks (Twitch Partner)

Twitch Partners can use up to 3 separate audio streams:

- **Track 1**: Main audio (Stream + VOD) - Always active
- **Track 2**: Stream-only audio (not in VOD) - Optional
- **Track 3**: VOD-only audio (not in stream) - Optional

**Use Cases:**
- Copyrighted music only in stream (Track 2), muted in VOD
- Alternative commentary track only for VOD (Track 3)
- Separate microphone and desktop audio tracks

**Configuration:**
```yaml
multi_audio_enabled: true
audio_tracks: 3
audio_sources:
  - 'audio=Microphone'  # Additional audio source
  - 'audio=Desktop'     # Desktop audio
```

**OBS Configuration:**
The RTMP stream from OBS must contain multiple audio streams. In OBS, this can be configured via the Audio Mixer settings and advanced audio properties (separate tracks for different audio sources).

## API Endpoints

The application provides the following REST API:

### Stream Control

```bash
# Start stream
curl -X POST http://localhost:5000/api/start

# Stop stream
curl -X POST http://localhost:5000/api/stop

# Get status
curl http://localhost:5000/api/status
```

### Media Management

```bash
# Upload file
curl -X POST -F "file=@image.jpg" http://localhost:5000/api/upload

# Set fallback
curl -X POST -H "Content-Type: application/json" \
  -d '{"type":"image","filename":"image.jpg"}' \
  http://localhost:5000/api/set_fallback

# Delete file
curl -X POST -H "Content-Type: application/json" \
  -d '{"filename":"image.jpg"}' \
  http://localhost:5000/api/delete_media
```

## Project Structure

```
twitch_fallback/
├── app.py                 # Flask web application
├── stream_manager.py      # Stream manager logic
├── Dockerfile            # Docker image for stream manager
├── docker-compose.yml    # Docker Compose configuration
├── nginx.conf           # NGINX RTMP server configuration
├── requirements.txt     # Python dependencies
├── config.yml           # Configuration file (not in Git)
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── config.html
│   └── media.html
├── media/              # Fallback media (not in Git)
│   └── .gitkeep
└── README.md
```

## Troubleshooting

### Stream Won't Start

1. Check the logs:
   ```bash
   docker-compose logs -f stream_manager
   ```

2. Ensure the RTMP stream from OBS is reachable:
   ```bash
   ffprobe rtmp://localhost:1935/input/obs
   ```

3. Verify the Twitch stream key configuration

4. Ensure OBS is streaming to the correct RTMP server

### Fallback Not Working

1. Check if the fallback file exists:
   ```bash
   ls -la media/
   ```

2. Ensure the file path in the config is correct

3. Check file permissions

### Twitch Stream Drops

1. Reduce the bitrate in the configuration
2. Check your internet connection
3. Ensure the stream key is correct

## Development

### Local Development Without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (system-wide required)
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg
# Windows: https://ffmpeg.org/download.html

# Start application
python app.py
```

### Tests

```bash
# Unit tests (TODO)
pytest

# Integration tests (TODO)
pytest tests/integration
```

## Feature Status

- ✅ Web UI for configuration
- ✅ Media upload and gallery
- ✅ Seamless streaming
- ✅ Multi-audio track support (Twitch Partner)
- ⏳ Authentication (Username/Password)
- ⏳ RTMP token protection
- ⏳ Multi-platform streaming (YouTube, Facebook, etc.)
- ⏳ Stream recording
- ⏳ Stream statistics and analytics
- ⏳ Webhook notifications

## License

[MIT License](LICENSE)

## Support

For questions or issues, please create an issue in the GitHub repository.

## Credits

- FFmpeg for video encoding
- NGINX-RTMP for the local RTMP server
- Flask for the web application
