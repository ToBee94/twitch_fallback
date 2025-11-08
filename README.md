# Twitch Stream Manager mit Fallback

Ein professioneller Stream Manager, der RTMP-Streams von OBS zu Twitch weiterleitet und bei Unterbrechungen automatisch ein Fallback-Bild oder -Video abspielt.

## Features

- 🎥 **OBS zu Twitch**: Leitet RTMP-Streams von OBS nahtlos an Twitch weiter
- 🔄 **Automatischer Fallback**: Wechselt bei Stream-Unterbrechung zu Fallback-Media (Bild oder Video)
- 🎵 **Multi-Audio-Tracks**: Separate Tonspuren für Stream und VOD (Twitch Partner)
- 🌐 **Web-Interface**: Benutzerfreundliche Browser-Konfiguration
- 📁 **Media-Galerie**: Upload und Verwaltung von Fallback-Bildern und -Videos
- 🔒 **Authentifizierung**: Login-Schutz für die Web-UI (geplant)
- 🔑 **Token-Schutz**: RTMP-Stream-Schutz mit Token (geplant)
- 🚀 **Nahtloses Streaming**: Keine Unterbrechungen bei Twitch durch lokalen RTMP-Buffer
- 🐳 **Docker**: Einfaches Deployment mit Docker Compose

## Architektur

Die Anwendung nutzt einen 2-Stufen-Ansatz für nahtloses Streaming:

1. **OBS** → **Lokaler RTMP-Server** (input app)
2. **Stream Manager** liest von **Lokaler RTMP-Server** oder nutzt **Fallback** → **Twitch**

Beim Wechsel zwischen OBS-Stream und Fallback wird nur die Input-Quelle gewechselt, während der Output zu Twitch durchgehend läuft.

## Voraussetzungen

- Docker und Docker Compose
- Twitch-Account mit Stream Key
- OBS Studio (oder andere RTMP-fähige Streaming-Software)

## Installation

### 1. Repository klonen

```bash
git clone <repository-url>
cd twitch_fallback
```

### 2. Konfiguration vorbereiten

Erstelle eine `config.yml` Datei (siehe `config.example.yml`):

```yaml
rtmp_input_url: 'rtmp://rtmp:1935/input/obs'
twitch_rtmp_url: 'rtmp://live.twitch.tv/app'
twitch_stream_key: 'DEIN_TWITCH_STREAM_KEY'
fallback_type: 'image'  # 'image' oder 'video'
fallback_image: 'media/fallback.jpg'
fallback_video: 'media/fallback.mp4'
rtmp_timeout: 5
check_interval: 2
video_bitrate: '2500k'
audio_bitrate: '160k'
fps: 30
resolution: '1920x1080'
```

### 3. Fallback-Media bereitstellen

Lege ein Fallback-Bild oder -Video im `media/` Ordner ab:

```bash
# Beispiel: Fallback-Bild
cp dein-fallback-bild.jpg media/fallback.jpg

# Oder: Fallback-Video
cp dein-fallback-video.mp4 media/fallback.mp4
```

### 4. Docker Container starten

```bash
docker-compose up -d
```

Die Web-UI ist nun unter `http://localhost:5000` erreichbar.

## Verwendung

### Web-Interface

1. Öffne `http://localhost:5000` im Browser
2. Navigiere zu **Konfiguration** und trage deine Einstellungen ein
3. Gehe zu **Medien** um Fallback-Bilder/-Videos hochzuladen
4. Starte den Stream im **Dashboard**

### OBS einrichten

Konfiguriere OBS, um zum lokalen RTMP-Server zu streamen:

1. **Öffne OBS Studio**
2. **Gehe zu Einstellungen → Stream**
3. **Wähle "Custom" als Service**
4. **Server:** `rtmp://localhost:1935/input`
5. **Stream Key:** `obs`
6. **Klicke auf "OK" und "Streaming starten"**

**Für Docker (wenn OBS auf anderem Rechner läuft):**
- Ersetze `localhost` mit der IP-Adresse des Docker-Hosts
- Stelle sicher, dass Port 1935 von außen erreichbar ist

### Empfohlene Twitch-Einstellungen

| Qualität | Auflösung | FPS | Video Bitrate | Audio Bitrate | Audio Tracks |
|----------|-----------|-----|---------------|---------------|--------------|
| Niedrig | 854x480 | 30 | 1000k | 128k | 1 |
| Mittel | 1280x720 | 30 | 2500k | 160k | 1 |
| Hoch (Partner) | 1920x1080 | 60 | 6000k | 160k | 1-3 |

**Hinweis:** Twitch begrenzt die maximale Bitrate auf ca. 6000 kbit/s. Für Nicht-Partner wird 2500-4500 kbit/s empfohlen.

### Multi-Audio-Tracks (Twitch Partner)

Twitch Partner können bis zu 3 separate Audiostreams verwenden:

- **Track 1**: Haupt-Audio (Stream + VOD) - Immer aktiv
- **Track 2**: Stream-Only Audio (nur Live, nicht im VOD) - Optional
- **Track 3**: VOD-Only Audio (nur in Aufzeichnung, nicht live) - Optional

**Anwendungsfälle:**
- Urheberrechtlich geschützte Musik nur im Stream (Track 2), die im VOD stumm geschaltet wird
- Alternative Kommentar-Spur nur für VOD (Track 3)
- Separate Mikrofon- und Desktop-Audio-Spuren

**Konfiguration:**
```yaml
multi_audio_enabled: true
audio_tracks: 3
audio_sources:
  - 'audio=Mikrofon'  # Zusätzliche Audio-Quelle
  - 'audio=Desktop'   # Desktop-Audio
```

**OBS-Konfiguration:**
Der RTMP-Stream von OBS muss mehrere Audiostreams enthalten. In OBS kann dies über die Audio-Mixer-Einstellungen und erweiterte Audio-Eigenschaften konfiguriert werden (separate Tracks für verschiedene Audioquellen).

## API-Endpunkte

Die Anwendung stellt folgende REST-API bereit:

### Stream-Kontrolle

```bash
# Stream starten
curl -X POST http://localhost:5000/api/start

# Stream stoppen
curl -X POST http://localhost:5000/api/stop

# Status abrufen
curl http://localhost:5000/api/status
```

### Media-Verwaltung

```bash
# Datei hochladen
curl -X POST -F "file=@bild.jpg" http://localhost:5000/api/upload

# Fallback setzen
curl -X POST -H "Content-Type: application/json" \
  -d '{"type":"image","filename":"bild.jpg"}' \
  http://localhost:5000/api/set_fallback

# Datei löschen
curl -X POST -H "Content-Type: application/json" \
  -d '{"filename":"bild.jpg"}' \
  http://localhost:5000/api/delete_media
```

## Projektstruktur

```
twitch_fallback/
├── app.py                 # Flask Web-Anwendung
├── stream_manager.py      # Stream-Manager Logik
├── Dockerfile            # Docker-Image für Stream Manager
├── docker-compose.yml    # Docker Compose Konfiguration
├── nginx.conf           # NGINX RTMP Server Konfiguration
├── requirements.txt     # Python Dependencies
├── config.yml           # Konfigurationsdatei (nicht in Git)
├── templates/           # HTML-Templates
│   ├── base.html
│   ├── index.html
│   ├── config.html
│   └── media.html
├── media/              # Fallback-Medien (nicht in Git)
│   └── .gitkeep
└── README.md
```

## Fehlerbehebung

### Stream startet nicht

1. Überprüfe die Logs:
   ```bash
   docker-compose logs -f stream_manager
   ```

2. Stelle sicher, dass der RTMP-Stream von OBS erreichbar ist:
   ```bash
   ffprobe rtmp://localhost:1935/input/obs
   ```

3. Prüfe die Twitch-Stream-Key Konfiguration

4. Stelle sicher, dass OBS zum richtigen RTMP-Server streamt

### Fallback funktioniert nicht

1. Überprüfe, ob die Fallback-Datei existiert:
   ```bash
   ls -la media/
   ```

2. Stelle sicher, dass der Dateipfad in der Config korrekt ist

3. Prüfe die Dateiberechtigungen

### Twitch-Stream bricht ab

1. Reduziere die Bitrate in der Konfiguration
2. Überprüfe deine Internet-Verbindung
3. Stelle sicher, dass der Stream Key korrekt ist

## Entwicklung

### Lokale Entwicklung ohne Docker

```bash
# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt

# FFmpeg installieren (system-weit erforderlich)
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg
# Windows: https://ffmpeg.org/download.html

# Anwendung starten
python app.py
```

### Tests

```bash
# Unit-Tests (TODO)
pytest

# Integration-Tests (TODO)
pytest tests/integration
```

## Feature Status

- ✅ Web-UI für Konfiguration
- ✅ Media-Upload und -Galerie
- ✅ Nahtloses Streaming
- ✅ Multi-Audio-Track Support (Twitch Partner)
- ⏳ Authentifizierung (Username/Password)
- ⏳ RTMP Token-Schutz
- ⏳ Multi-Platform Streaming (YouTube, Facebook, etc.)
- ⏳ Stream-Aufzeichnung
- ⏳ Stream-Statistiken und Analytics
- ⏳ Webhook-Benachrichtigungen

## Lizenz

[MIT License](LICENSE)

## Support

Bei Fragen oder Problemen erstelle bitte ein Issue im GitHub-Repository.

## Credits

- FFmpeg für Video-Encoding
- NGINX-RTMP für den lokalen RTMP-Server
- Flask für die Web-Anwendung
