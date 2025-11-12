#!/usr/bin/env python3
"""
ScreenPulse - Automatic screen recorder triggered by mouse movement
Records screen activity when mouse moves, stops after inactivity, and splits long recordings.
"""

import subprocess
import time
import os
import logging
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
import evdev
import select
import signal
import sys
import atexit

class ScreenPulse:
    def __init__(self,
                 output_dir="recordings",
                 log_file="screenpulse.log",
                 max_duration=40 * 60,  # 40 minutes in seconds
                 idle_timeout=10 * 60,  # 10 minutes in seconds
                 resolution="1280x720",
                 crf=25):  # Compression quality (18-28, lower = better quality/larger file)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.log_file = Path(log_file)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.max_duration = max_duration
        self.idle_timeout = idle_timeout
        self.resolution = resolution
        self.crf = crf

        self.is_recording = False
        self.ffmpeg_process = None
        self.last_mouse_time = time.time()
        self.recording_start_time = None
        self.lock = Lock()

        self.current_filename = None

        self.logger.info("ScreenPulse initialized")
        self.logger.info(f"Output directory: {self.output_dir.absolute()}")
        self.logger.info(f"Log file: {self.log_file.absolute()}")
        self.logger.info(f"Max recording duration: {max_duration // 60} minutes")
        self.logger.info(f"Idle timeout: {idle_timeout // 60} minutes")
        self.logger.info(f"Resolution: {resolution}")
        self.logger.info(f"Quality (CRF): {crf}")

    def get_output_filename(self):
        """Generate timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"recording_{timestamp}.mp4"

    def get_ffmpeg_command(self, output_file):
        """Build optimized ffmpeg command for small file size and good quality"""
        # Detect display server (X11 or Wayland)
        display = os.environ.get('DISPLAY')
        wayland_display = os.environ.get('WAYLAND_DISPLAY')

        if wayland_display:
            # Wayland - use wf-recorder with software encoding
            self.logger.info("Detected Wayland - using wf-recorder")
            return [
                'wf-recorder',
                '-f', str(output_file),
                '-c', 'libx264',  # Software encoding (h264_vaapi may fail)
                '--pixel-format', 'yuv420p',
                '-r', '30'  # 30 fps
            ]
        else:
            # X11 - use ffmpeg with x11grab
            return [
                'ffmpeg',
                '-f', 'x11grab',
                '-video_size', self.resolution,
                '-framerate', '30',
                '-i', display or ':0',
                '-c:v', 'libx264',
                '-preset', 'medium',  # Balance between speed and compression
                '-crf', str(self.crf),  # Quality setting
                '-pix_fmt', 'yuv420p',  # Compatibility
                '-movflags', '+faststart',  # Enable streaming
                '-vf', f'scale={self.resolution}:flags=lanczos',  # High-quality scaling
                '-y',  # Overwrite output file
                str(output_file)
            ]

    def start_recording(self):
        """Start ffmpeg recording process"""
        with self.lock:
            if self.is_recording:
                return

            self.current_filename = self.get_output_filename()
            self.recording_start_time = time.time()

            cmd = self.get_ffmpeg_command(self.current_filename)

            try:
                # Start ffmpeg in background, suppress output
                self.ffmpeg_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.PIPE
                )
                self.is_recording = True
                self.logger.info(f"▶ Recording started: {self.current_filename.name}")
            except FileNotFoundError as e:
                self.logger.error(f"Recording tool not found. Please install ffmpeg or wf-recorder")
                self.logger.error(f"Details: {e}")
            except Exception as e:
                self.logger.error(f"Error starting recording: {e}")

    def stop_recording(self):
        """Stop current recording"""
        with self.lock:
            if not self.is_recording:
                return

            if self.ffmpeg_process:
                # Send 'q' to ffmpeg for graceful shutdown
                try:
                    self.ffmpeg_process.communicate(input=b'q', timeout=5)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait(timeout=5)
                except:
                    pass

                self.ffmpeg_process = None

            duration = int(time.time() - self.recording_start_time)
            self.is_recording = False

            # Get file size
            if self.current_filename.exists():
                size_mb = self.current_filename.stat().st_size / (1024 * 1024)
                self.logger.info(f"■ Recording stopped: {self.current_filename.name}")
                self.logger.info(f"  Duration: {duration // 60}m {duration % 60}s | Size: {size_mb:.1f} MB")
            else:
                self.logger.warning(f"■ Recording stopped (file not created)")

    def get_input_devices(self):
        """Get all input devices that can trigger recording"""
        devices = []
        try:
            for device_path in evdev.list_devices():
                try:
                    device = evdev.InputDevice(device_path)
                    # Only include devices that have mouse or keyboard capabilities
                    caps = device.capabilities()
                    if evdev.ecodes.EV_REL in caps or evdev.ecodes.EV_KEY in caps:
                        devices.append(device)
                        self.logger.debug(f"Monitoring device: {device.name} ({device_path})")
                except Exception as e:
                    self.logger.warning(f"Could not access {device_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error listing input devices: {e}")
        return devices

    def on_input_activity(self):
        """Handle input activity (mouse/keyboard)"""
        self.last_mouse_time = time.time()

        # Start recording if not already recording
        if not self.is_recording:
            self.start_recording()

    def monitor_recording(self):
        """Monitor recording duration and idle time"""
        while True:
            time.sleep(1)

            if self.is_recording:
                current_time = time.time()
                recording_duration = current_time - self.recording_start_time
                idle_duration = current_time - self.last_mouse_time

                # Check if max duration reached
                if recording_duration >= self.max_duration:
                    self.logger.info(f"Max duration ({self.max_duration // 60} min) reached")
                    self.stop_recording()
                    # Recording will auto-restart on next mouse movement

                # Check if idle timeout reached
                elif idle_duration >= self.idle_timeout:
                    self.logger.info(f"Idle timeout ({self.idle_timeout // 60} min) reached")
                    self.stop_recording()

    def run(self):
        """Main run loop"""
        self.logger.info("="*60)
        self.logger.info("ScreenPulse is running!")
        self.logger.info("Move your mouse or press any key to start recording...")
        self.logger.info("="*60)

        # Get input devices
        devices = self.get_input_devices()
        if not devices:
            self.logger.error("No input devices found! Make sure you're in the 'input' group.")
            self.logger.error("Run: sudo usermod -aG input $USER")
            sys.exit(1)

        self.logger.info(f"Monitoring {len(devices)} input device(s)")

        # Start monitoring thread
        monitor_thread = Thread(target=self.monitor_recording, daemon=True)
        monitor_thread.start()

        # Monitor input devices using evdev
        try:
            while True:
                # Use select to wait for events on any device
                r, w, x = select.select(devices, [], [], 1.0)
                for device in r:
                    try:
                        for event in device.read():
                            # Detect mouse movement or keyboard activity
                            if event.type in (evdev.ecodes.EV_REL, evdev.ecodes.EV_KEY):
                                self.on_input_activity()
                    except OSError as e:
                        # Device was disconnected, refresh device list
                        self.logger.warning(f"Device disconnected: {device.name}")
                        devices = self.get_input_devices()
                        break
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.stop_recording()
            self.logger.info("ScreenPulse stopped.")
            sys.exit(0)
        except Exception as e:
            self.logger.error(f"Error in input monitoring: {e}")
            self.stop_recording()
            sys.exit(1)
        finally:
            # Close all devices
            for device in devices:
                try:
                    device.close()
                except:
                    pass

def daemonize(pid_file):
    """Daemonize the process"""
    # Check if already running
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            old_pid = f.read().strip()
        try:
            # Check if process is still running
            os.kill(int(old_pid), 0)
            print(f"ScreenPulse is already running (PID: {old_pid})")
            sys.exit(1)
        except (OSError, ValueError):
            # Process not running, remove stale PID file
            os.remove(pid_file)

    # Fork to background
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process - write PID and exit
            with open(pid_file, 'w') as f:
                f.write(str(pid))
            print(f"ScreenPulse started in background (PID: {pid})")
            print(f"Log file: screenpulse.log")
            print(f"Stop with: kill {pid} or delete {pid_file} and kill manually")
            sys.exit(0)
    except OSError as e:
        print(f"Fork failed: {e}")
        sys.exit(1)

    # Child process continues
    # Detach from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # Setup cleanup on exit
    def cleanup():
        if os.path.exists(pid_file):
            os.remove(pid_file)
    atexit.register(cleanup)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='ScreenPulse - Motion-triggered screen recorder')
    parser.add_argument('--daemon', action='store_true', help='Run in background as daemon')
    parser.add_argument('--output-dir', default='recordings', help='Output directory for recordings')
    parser.add_argument('--log-file', default='screenpulse.log', help='Log file path')
    parser.add_argument('--pid-file', default='screenpulse.pid', help='PID file path')
    parser.add_argument('--max-duration', type=int, default=2400, help='Max recording duration in seconds (default: 2400 = 40 min)')
    parser.add_argument('--idle-timeout', type=int, default=600, help='Idle timeout in seconds (default: 600 = 10 min)')
    parser.add_argument('--resolution', default='1280x720', help='Recording resolution (default: 1280x720)')
    parser.add_argument('--crf', type=int, default=25, help='Video quality CRF (18-28, lower = better, default: 25)')
    args = parser.parse_args()

    # Daemonize if requested
    if args.daemon:
        daemonize(args.pid_file)

    # Handle Ctrl+C gracefully
    recorder = ScreenPulse(
        output_dir=args.output_dir,
        log_file=args.log_file,
        max_duration=args.max_duration,
        idle_timeout=args.idle_timeout,
        resolution=args.resolution,
        crf=args.crf
    )

    def signal_handler(sig, frame):
        recorder.logger.info("Shutting down...")
        recorder.stop_recording()
        # Clean up PID file if in daemon mode
        if args.daemon and os.path.exists(args.pid_file):
            os.remove(args.pid_file)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    recorder.run()

if __name__ == "__main__":
    main()
