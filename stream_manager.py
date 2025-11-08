#!/usr/bin/env python3
"""
Twitch Stream Manager with RTMP Input and Fallback
Forwards RTMP stream from OBS to Twitch and uses fallback media on interruption
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
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamManager:
    def __init__(self, config_path='config.yml', register_signals=False):
        """Initialize Stream Manager with configuration"""
        self.config = self._load_config(config_path)
        self.input_process = None  # RTMP from OBS or Fallback to local RTMP
        self.relay_process = None  # Local RTMP to Twitch (always running)
        self.shutdown_event = Event()
        self.is_rtmp_input_active = False
        self.local_rtmp = 'rtmp://rtmp:1935/live'  # Docker service name

        # Signal handler for clean shutdown (only in main thread)
        if register_signals:
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except ValueError:
                # Signals can only be registered in main thread
                logger.warning("Cannot register signal handlers (not in main thread)")

    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate required configurations
        required = ['rtmp_input_url', 'twitch_rtmp_url', 'twitch_stream_key']
        for key in required:
            if key not in config:
                raise ValueError(f"Missing configuration: {key}")

        # Set defaults
        config.setdefault('fallback_type', 'image')  # 'image' or 'video'
        config.setdefault('fallback_image', 'media/fallback.jpg')
        config.setdefault('fallback_video', 'media/fallback.mp4')
        config.setdefault('rtmp_timeout', 5)  # seconds
        config.setdefault('check_interval', 2)  # seconds
        config.setdefault('video_bitrate', '2500k')
        config.setdefault('audio_bitrate', '160k')
        config.setdefault('fps', 30)
        config.setdefault('resolution', '1920x1080')

        # Multi-audio track configuration (for Twitch Partner)
        config.setdefault('multi_audio_enabled', False)
        config.setdefault('audio_tracks', 1)  # 1-3 tracks supported
        config.setdefault('audio_sources', [])  # Additional audio inputs

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

    def check_rtmp_stream(self):
        """Check if RTMP stream from OBS is available"""
        try:
            # Use ffprobe to check RTMP stream
            # For RTMP, we need to specify the stream name (obs) explicitly
            stream_url = f"{self.config['rtmp_input_url']}/obs"

            cmd = [
                'ffprobe',
                '-v', 'error',
                '-i', stream_url,
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1',
                '-rw_timeout', str(self.config['rtmp_timeout'] * 1000000)  # microseconds
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.config['rtmp_timeout'] + 2
            )

            if result.returncode != 0:
                logger.warning(f"RTMP check failed for {stream_url}: {result.stderr.decode()}")
            else:
                logger.info(f"RTMP check successful for {stream_url}")

            return result.returncode == 0
        except Exception as e:
            logger.error(f"RTMP input check failed: {e}")
            return False

    def _build_audio_encoding_options(self):
        """Build audio encoding options for multi-track support"""
        options = []

        if self.config.get('multi_audio_enabled', False):
            # Multi-track audio (Twitch Partner feature)
            num_tracks = min(self.config.get('audio_tracks', 1), 3)  # Twitch supports max 3 tracks

            for i in range(num_tracks):
                # Map audio stream
                options.extend(['-map', f'0:a:{i}?'])  # ? makes it optional

                # Audio encoding per track
                options.extend([
                    f'-c:a:{i}', 'aac',
                    f'-b:a:{i}', self.config['audio_bitrate'],
                    f'-ar:{i}', '44100',
                    f'-ac:{i}', '2'
                ])
        else:
            # Single audio track (standard)
            options.extend([
                '-c:a', 'aac',
                '-b:a', self.config['audio_bitrate'],
                '-ar', '44100',
                '-ac', '2'
            ])

        return options

    def build_input_command(self, use_rtmp_input=True):
        """Build FFmpeg command for RTMP input from OBS or fallback to local RTMP"""
        if use_rtmp_input:
            # RTMP stream from OBS to local RTMP buffer
            # Construct full stream URL with stream name
            stream_url = f"{self.config['rtmp_input_url']}/obs"

            cmd = [
                'ffmpeg',
                '-i', stream_url,
            ]

            # Add additional audio sources if configured
            for audio_source in self.config.get('audio_sources', []):
                cmd.extend(['-i', audio_source])

            # Video encoding
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-b:v', self.config['video_bitrate'],
                '-maxrate', self.config['video_bitrate'],
                '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                '-s', self.config['resolution'],
                '-r', str(self.config['fps']),
                '-g', str(self.config['fps'] * 2),  # keyframe every 2 seconds
                '-pix_fmt', 'yuv420p',
            ])

            # Audio encoding (with multi-track support)
            cmd.extend(self._build_audio_encoding_options())

            # Output to local RTMP
            cmd.extend([
                '-f', 'flv',
                f'{self.local_rtmp}'
            ])
            return cmd
        else:
            # Fallback (image or video) to local RTMP
            if self.config['fallback_type'] == 'image':
                cmd = [
                    'ffmpeg',
                    '-loop', '1',
                    '-framerate', str(self.config['fps']),
                    '-i', self.config['fallback_image'],
                ]

                # Generate silent audio for multi-track if enabled
                if self.config.get('multi_audio_enabled', False):
                    num_tracks = min(self.config.get('audio_tracks', 1), 3)
                    for i in range(num_tracks):
                        cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
                else:
                    cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])

                # Video encoding
                cmd.extend([
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-b:v', self.config['video_bitrate'],
                    '-maxrate', self.config['video_bitrate'],
                    '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                    '-s', self.config['resolution'],
                    '-r', str(self.config['fps']),
                    '-g', str(self.config['fps'] * 2),
                    '-pix_fmt', 'yuv420p',
                ])

                # Audio encoding (with multi-track support)
                cmd.extend(self._build_audio_encoding_options())
                cmd.extend(['-shortest'])

                # Output to local RTMP
                cmd.extend([
                    '-f', 'flv',
                    f'{self.local_rtmp}'
                ])
            else:  # video
                cmd = [
                    'ffmpeg',
                    '-stream_loop', '-1',  # loop video
                    '-re',  # realtime
                    '-i', self.config['fallback_video'],
                ]

                # Video encoding
                cmd.extend([
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-b:v', self.config['video_bitrate'],
                    '-maxrate', self.config['video_bitrate'],
                    '-bufsize', str(int(self.config['video_bitrate'].rstrip('k')) * 2) + 'k',
                    '-s', self.config['resolution'],
                    '-r', str(self.config['fps']),
                    '-g', str(self.config['fps'] * 2),
                    '-pix_fmt', 'yuv420p',
                ])

                # Audio encoding (with multi-track support)
                cmd.extend(self._build_audio_encoding_options())

                # Output to local RTMP
                cmd.extend([
                    '-f', 'flv',
                    f'{self.local_rtmp}'
                ])

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

    def start_input_stream(self, use_rtmp_input=True):
        """Start input FFmpeg process (RTMP from OBS or Fallback to local RTMP)"""
        if self.input_process:
            logger.info("Stopping current input stream...")
            self.input_process.terminate()
            try:
                self.input_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.input_process.kill()

        cmd = self.build_input_command(use_rtmp_input)
        source = "RTMP (OBS)" if use_rtmp_input else "Fallback"
        logger.info(f"Starting input stream from {source}...")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        self.input_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        self.is_rtmp_input_active = use_rtmp_input
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
        """Monitor stream and switch between RTMP input and fallback"""
        logger.info("Stream monitoring started")

        while not self.shutdown_event.is_set():
            # Only check RTMP availability if we're NOT already using it
            # (to avoid conflicts with the input process reading from the same stream)
            if self.is_rtmp_input_active:
                rtmp_available = True  # Assume it's available if we're using it
            else:
                rtmp_available = self.check_rtmp_stream()

            # Switch to RTMP input if available and not active
            if rtmp_available and not self.is_rtmp_input_active:
                logger.info("RTMP stream from OBS detected, switching from fallback to RTMP...")
                self.start_input_stream(use_rtmp_input=True)

            # Don't actively check if RTMP is lost - let the process crash detection handle it
            # (checking while input is reading causes conflicts)

            # Check if input process is still running
            if self.input_process and self.input_process.poll() is not None:
                # Read stderr to see why it crashed
                stderr_output = self.input_process.stderr.read().decode('utf-8', errors='ignore')
                logger.error(f"Input FFmpeg process unexpectedly terminated!")
                logger.error(f"FFmpeg stderr: {stderr_output[-500:]}")  # Last 500 chars
                self.start_input_stream(use_rtmp_input=rtmp_available)

            # Check if relay process is still running (critical!)
            if self.relay_process and self.relay_process.poll() is not None:
                # Read stderr to see why it crashed
                stderr_output = self.relay_process.stderr.read().decode('utf-8', errors='ignore')
                logger.error(f"Relay FFmpeg process unexpectedly terminated!")
                logger.error(f"FFmpeg stderr: {stderr_output[-500:]}")  # Last 500 chars
                self.relay_process = None
                self.start_relay_stream()

            time.sleep(self.config['check_interval'])

    def stop(self):
        """Stop the stream manager gracefully"""
        logger.info("Stopping stream manager...")
        self.shutdown_event.set()

        # Terminate processes
        if self.input_process:
            self.input_process.terminate()
            try:
                self.input_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.input_process.kill()

        if self.relay_process:
            self.relay_process.terminate()
            try:
                self.relay_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.relay_process.kill()

    def run(self):
        """Main loop: Start stream and monitoring"""
        logger.info("Starting Twitch Stream Manager...")

        # Determine initial stream source
        rtmp_available = self.check_rtmp_stream()

        # Start input stream (RTMP from OBS or fallback)
        if rtmp_available:
            logger.info("RTMP stream from OBS available, starting with RTMP input...")
            self.start_input_stream(use_rtmp_input=True)
        else:
            logger.info("RTMP stream from OBS not available, starting with fallback...")
            self.start_input_stream(use_rtmp_input=False)

        # Start relay stream to Twitch (runs continuously)
        self.start_relay_stream()

        # Monitoring loop
        try:
            self.monitor_stream()
        except Exception as e:
            logger.error(f"Error in stream manager: {e}")
            raise
        finally:
            self.stop()


if __name__ == "__main__":
    try:
        # Register signals when running as main program
        manager = StreamManager(register_signals=True)
        manager.run()
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
