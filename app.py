#!/usr/bin/env python3
"""
Flask Web App for Twitch Stream Manager
Provides browser interface for configuration and stream control
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import yaml
import os
from pathlib import Path
import threading
import logging
from werkzeug.utils import secure_filename
from stream_manager import StreamManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'media'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'webm'}

# Global variables
stream_manager = None
stream_thread = None
CONFIG_FILE = 'config.yml'

# Ensure media directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_config():
    """Load current configuration"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    else:
        # Default configuration
        return {
            'rtsp_url': 'rtsp://localhost:8554/live',
            'twitch_rtmp_url': 'rtmp://live.twitch.tv/app',
            'twitch_stream_key': '',
            'fallback_type': 'image',
            'fallback_image': 'media/fallback.jpg',
            'fallback_video': 'media/fallback.mp4',
            'rtsp_timeout': 5,
            'check_interval': 2,
            'video_bitrate': '2500k',
            'audio_bitrate': '160k',
            'fps': 30,
            'resolution': '1920x1080'
        }


def save_config(config):
    """Save configuration"""
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def get_stream_status():
    """Get current stream status"""
    global stream_manager, stream_thread

    if stream_manager is None or stream_thread is None or not stream_thread.is_alive():
        return {
            'running': False,
            'source': 'none',
            'rtsp_available': False
        }

    return {
        'running': True,
        'source': 'rtsp' if stream_manager.is_rtsp_active else 'fallback',
        'rtsp_available': stream_manager.check_rtsp_stream()
    }


def get_media_files():
    """Get list of media files in upload folder"""
    media_dir = Path(app.config['UPLOAD_FOLDER'])
    files = {
        'images': [],
        'videos': []
    }

    if not media_dir.exists():
        return files

    image_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

    for file_path in media_dir.iterdir():
        if file_path.is_file():
            ext = file_path.suffix.lower()
            file_info = {
                'name': file_path.name,
                'path': f'media/{file_path.name}',
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime
            }

            if ext in image_extensions:
                files['images'].append(file_info)
            elif ext in video_extensions:
                files['videos'].append(file_info)

    # Sort by modification time (newest first)
    files['images'].sort(key=lambda x: x['modified'], reverse=True)
    files['videos'].sort(key=lambda x: x['modified'], reverse=True)

    return files


@app.route('/')
def index():
    """Main page"""
    config = load_config()
    status = get_stream_status()
    return render_template('index.html', config=config, status=status)


@app.route('/config', methods=['GET', 'POST'])
def config():
    """Configuration page"""
    if request.method == 'POST':
        # Save new configuration
        new_config = {
            'rtsp_url': request.form.get('rtsp_url'),
            'twitch_rtmp_url': request.form.get('twitch_rtmp_url'),
            'twitch_stream_key': request.form.get('twitch_stream_key'),
            'fallback_type': request.form.get('fallback_type'),
            'fallback_image': request.form.get('fallback_image'),
            'fallback_video': request.form.get('fallback_video'),
            'rtsp_timeout': int(request.form.get('rtsp_timeout', 5)),
            'check_interval': int(request.form.get('check_interval', 2)),
            'video_bitrate': request.form.get('video_bitrate'),
            'audio_bitrate': request.form.get('audio_bitrate'),
            'fps': int(request.form.get('fps', 30)),
            'resolution': request.form.get('resolution')
        }

        save_config(new_config)
        return redirect(url_for('index'))

    current_config = load_config()
    return render_template('config.html', config=current_config)


@app.route('/media')
def media():
    """Media gallery page"""
    config = load_config()
    files = get_media_files()
    return render_template('media.html', config=config, files=files)


@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload media file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save file
        file.save(file_path)

        return jsonify({
            'success': True,
            'message': 'Datei erfolgreich hochgeladen',
            'filename': filename,
            'path': f'media/{filename}'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Ungültiger Dateityp'
        }), 400


@app.route('/api/delete_media', methods=['POST'])
def delete_media():
    """Delete media file"""
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({'success': False, 'message': 'Kein Dateiname angegeben'}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'success': True, 'message': 'Datei gelöscht'})
    else:
        return jsonify({'success': False, 'message': 'Datei nicht gefunden'}), 404


@app.route('/api/set_fallback', methods=['POST'])
def set_fallback():
    """Set fallback media file"""
    data = request.get_json()
    media_type = data.get('type')  # 'image' or 'video'
    filename = data.get('filename')

    if not media_type or not filename:
        return jsonify({'success': False, 'message': 'Fehlende Parameter'}), 400

    config = load_config()

    if media_type == 'image':
        config['fallback_image'] = f"media/{filename}"
        config['fallback_type'] = 'image'
    elif media_type == 'video':
        config['fallback_video'] = f"media/{filename}"
        config['fallback_type'] = 'video'
    else:
        return jsonify({'success': False, 'message': 'Ungültiger Typ'}), 400

    save_config(config)
    return jsonify({'success': True, 'message': 'Fallback-Medium aktualisiert'})


@app.route('/api/start', methods=['POST'])
def start_stream():
    """Start stream"""
    global stream_manager, stream_thread

    if stream_thread and stream_thread.is_alive():
        return jsonify({'success': False, 'message': 'Stream läuft bereits'}), 400

    try:
        stream_manager = StreamManager(CONFIG_FILE)
        stream_thread = threading.Thread(target=stream_manager.run, daemon=True)
        stream_thread.start()

        return jsonify({'success': True, 'message': 'Stream gestartet'})
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_stream():
    """Stop stream"""
    global stream_manager, stream_thread

    if stream_manager is None or stream_thread is None:
        return jsonify({'success': False, 'message': 'Kein Stream aktiv'}), 400

    try:
        stream_manager.shutdown_event.set()
        if stream_manager.input_process:
            stream_manager.input_process.terminate()
        if stream_manager.relay_process:
            stream_manager.relay_process.terminate()

        stream_thread.join(timeout=5)
        stream_manager = None
        stream_thread = None

        return jsonify({'success': True, 'message': 'Stream gestoppt'})
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Get stream status"""
    return jsonify(get_stream_status())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
