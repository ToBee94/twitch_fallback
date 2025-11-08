#!/usr/bin/env python3
"""
Twitch Stream Manager with RTSP Input and Fallback
Forwards RTSP stream to Twitch and uses fallback media on interruption
Uses local RTMP server for seamless switching
"""

import subprocess
import time
import logging
import signal
import sys
import os
from pathlib import Path
import yaml
from threading import Thread, Event

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamManager:
    def __init__(self, config_path='config.yml'):
        """Initialize Stream Manager with configuration"""
        self.config = self._load_config(config_path)
        self.input_process = None  # RTSP or Fallback to local RTMP
        self.relay_process = None  # Local RTMP to Twitch (always running)
        self.shutdown_event = Event()
        self.is_rtsp_active = False
        self.local_rtmp = 'rtmp://rtmp:1935/live'  # Docker service name

        # Signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate required configurations
        required = ['rtsp_url', 'twitch_rtmp_url', 'twitch_stream_key']
        for key in required:
            if key not in config:
                raise ValueError(f"Missing configuration: {key}")

        # Set defaults
        config.setdefault('fallback_type', 'image')  # 'image' or 'video'
        config.setdefault('fallback_image', 'media/fallback.jpg')
        config.setdefault('fallback_video', 'media/fallback.mp4')
        config.setdefault('rtsp_timeout', 5)  # seconds
        config.setdefault('check_interval', 2)  # seconds
        config.setdefault('video_bitrate', '2500k')
        config.setdefault('audio_bitrate', '160k')
        config.setdefault('fps', 30)
        config.setdefault('resolution', '1920x1080')

        return config

    def _signal_handler(self, signum, frame):
        """Handler for SIGINT/SIGTERM for clean shutdown"""
        logger.info("Shutdown signal received, stopping stream...")
        self.shutdown_event.set()

        if self.input_process:
            self.input_process.terminate()
            try:
                self.input_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.input_process.kill()

        if self.relay_process:
            self.relay_process.terminate()
            try:
                self.relay_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.relay_process.kill()

        sys.exit(0)

    def check_rtsp_stream(self):
        """Check if RTSP stream is available"""
        try:
            # Use ffprobe to check stream
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-rtsp_transport', 'tcp',
                '-timeout', str(self.config['rtsp_timeout'] * 1000000),  # microseconds
                '-i', self.config['rtsp_url'],
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1'
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.config['rtsp_timeout'] + 2
            )

            return result.returncode == 0
        except Exception as e:
            logger.debug(f"RTSP check failed: {e}")
            return False

    def build_input_command(self, use_rtsp=True):
        """Build FFmpeg command for RTSP or fallback to local RTMP"""
        if use_rtsp:
            # RTSP stream to local RTMP
            cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-timeout', str(self.config['rtsp_timeout'] * 1000000),
                '-i', self.config['rtsp_url'],
                # Video encoding
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-b:v', self.config['video_bitrate'],
                '-maxrate', self.config['video_bitrate'],
                '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                '-s', self.config['resolution'],
                '-r', str(self.config['fps']),
                '-g', str(self.config['fps'] * 2),  # keyframe every 2 seconds
                '-pix_fmt', 'yuv420p',
                # Audio encoding
                '-c:a', 'aac',
                '-b:a', self.config['audio_bitrate'],
                '-ar', '44100',
                '-ac', '2',
                # Output to local RTMP
                '-f', 'flv',
                f'{self.local_rtmp}'
            ]
        else:
            # Fallback (image or video) to local RTMP
            if self.config['fallback_type'] == 'image':
                cmd = [
                    'ffmpeg',
                    '-loop', '1',
                    '-framerate', str(self.config['fps']),
                    '-i', self.config['fallback_image'],
                    # Generate silent audio
                    '-f', 'lavfi',
                    '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                    # Video encoding
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-b:v', self.config['video_bitrate'],
                    '-maxrate', self.config['video_bitrate'],
                    '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                    '-s', self.config['resolution'],
                    '-r', str(self.config['fps']),
                    '-g', str(self.config['fps'] * 2),
                    '-pix_fmt', 'yuv420p',
                    # Audio encoding
                    '-c:a', 'aac',
                    '-b:a', self.config['audio_bitrate'],
                    '-ar', '44100',
                    '-shortest',
                    # Output to local RTMP
                    '-f', 'flv',
                    f'{self.local_rtmp}'
                ]
            else:  # video
                cmd = [
                    'ffmpeg',
                    '-stream_loop', '-1',  # loop video
                    '-re',  # realtime
                    '-i', self.config['fallback_video'],
                    # Video encoding
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-b:v', self.config['video_bitrate'],
                    '-maxrate', self.config['video_bitrate'],
                    '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                    '-s', self.config['resolution'],
                    '-r', str(self.config['fps']),
                    '-g', str(self.config['fps'] * 2),
                    '-pix_fmt', 'yuv420p',
                    # Audio encoding
                    '-c:a', 'aac',
                    '-b:a', self.config['audio_bitrate'],
                    '-ar', '44100',
                    '-ac', '2',
                    # Output to local RTMP
                    '-f', 'flv',
                    f'{self.local_rtmp}'
                ]

        return cmd

    def build_relay_command(self):
        """Build FFmpeg command for relaying local RTMP to Twitch"""
        twitch_url = f"{self.config['twitch_rtmp_url']}/{self.config['twitch_stream_key']}"

        cmd = [
            'ffmpeg',
            '-re',
            '-i', f'{self.local_rtmp}',
            # Copy codec (no re-encoding for efficiency)
            '-c', 'copy',
            # Output to Twitch
            '-f', 'flv',
            twitch_url
        ]

        return cmd

    def start_input_stream(self, use_rtsp=True):
        """Start input FFmpeg process (RTSP or Fallback to local RTMP)"""
        if self.input_process:
            logger.info("Stopping current input stream...")
            self.input_process.terminate()
            try:
                self.input_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.input_process.kill()

        cmd = self.build_input_command(use_rtsp)
        source = "RTSP" if use_rtsp else "Fallback"
        logger.info(f"Starting input stream from {source}...")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        self.input_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        self.is_rtsp_active = use_rtsp
        return self.input_process

    def start_relay_stream(self):
        """Start relay FFmpeg process (local RTMP to Twitch) - runs continuously"""
        if self.relay_process:
            logger.warning("Relay stream already running")
            return

        cmd = self.build_relay_command()
        logger.info("Starting relay stream to Twitch...")
        logger.debug(f"FFmpeg relay command: {' '.join(cmd)}")

        # Wait a bit for local RTMP to be ready
        time.sleep(2)

        self.relay_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        return self.relay_process

    def monitor_stream(self):
        """Monitor stream and switch between RTSP and fallback"""
        logger.info("Stream monitoring started")

        while not self.shutdown_event.is_set():
            rtsp_available = self.check_rtsp_stream()

            # Switch to RTSP if available and not active
            if rtsp_available and not self.is_rtsp_active:
                logger.info("RTSP stream detected, switching from fallback to RTSP...")
                self.start_input_stream(use_rtsp=True)

            # Switch to fallback if RTSP not available but active
            elif not rtsp_available and self.is_rtsp_active:
                logger.warning("RTSP stream lost, switching to fallback...")
                self.start_input_stream(use_rtsp=False)

            # Check if input process is still running
            if self.input_process and self.input_process.poll() is not None:
                logger.error("Input FFmpeg process unexpectedly terminated, restarting...")
                self.start_input_stream(use_rtsp=rtsp_available)

            # Check if relay process is still running (critical!)
            if self.relay_process and self.relay_process.poll() is not None:
                logger.error("Relay FFmpeg process unexpectedly terminated, restarting...")
                self.start_relay_stream()

            time.sleep(self.config['check_interval'])

    def run(self):
        """Main loop: Start stream and monitoring"""
        logger.info("Starting Twitch Stream Manager...")

        # Determine initial stream source
        rtsp_available = self.check_rtsp_stream()

        # Start input stream (RTSP or fallback)
        if rtsp_available:
            logger.info("RTSP stream available, starting with RTSP...")
            self.start_input_stream(use_rtsp=True)
        else:
            logger.info("RTSP stream not available, starting with fallback...")
            self.start_input_stream(use_rtsp=False)

        # Start relay stream to Twitch (runs continuously)
        self.start_relay_stream()

        # Monitoring loop
        try:
            self.monitor_stream()
        except Exception as e:
            logger.error(f"Error in stream manager: {e}")
            raise
        finally:
            if self.input_process:
                self.input_process.terminate()
            if self.relay_process:
                self.relay_process.terminate()


if __name__ == "__main__":
    try:
        manager = StreamManager()
        manager.run()
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
