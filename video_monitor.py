"""File system monitor for detecting new videos."""
import logging
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import config

logger = logging.getLogger(__name__)


class VideoHandler(FileSystemEventHandler):
    """Handles file system events for video files."""

    def __init__(self, callback):
        """
        Initialize the video handler.

        Args:
            callback: Function to call when a new video is detected.
                     Should accept a Path object as argument.
        """
        self.callback = callback
        self.processing = set()  # Track files being processed

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        self._process_video_file(file_path, "created")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        self._process_video_file(file_path, "modified")

    def _process_video_file(self, file_path: Path, event_type: str):
        """Process a video file event."""
        # Check if it's a supported video format
        if file_path.suffix.lower() not in config.SUPPORTED_FORMATS:
            logger.debug(f"Ignoring non-video file: {file_path.name}")
            return

        # Avoid processing the same file multiple times
        if file_path in self.processing:
            logger.debug(f"Already processing: {file_path.name}")
            return

        logger.info(f"Video {event_type}: {file_path.name}")

        # Wait for file to be fully written
        self._wait_for_stable_file(file_path)

        # Mark as processing
        self.processing.add(file_path)

        try:
            # Call the callback with the video path
            self.callback(file_path)
        finally:
            # Remove from processing set
            self.processing.discard(file_path)

    def _wait_for_stable_file(self, file_path: Path, timeout: int = 600):
        """
        Wait for file to finish being written (recording stopped).

        Args:
            file_path: Path to the file
            timeout: Maximum seconds to wait (default: 600s = 10 minutes)

        Raises:
            TimeoutError: If file doesn't stabilize within timeout
        """
        logger.debug(f"Waiting for recording to complete: {file_path.name}")

        start_time = time.time()
        stable_count = 0
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size

                # Check if file size is stable
                if current_size == last_size:
                    if current_size >= config.MIN_FILE_SIZE:
                        stable_count += 1
                        logger.debug(f"Stable check {stable_count}/{config.STABILITY_CHECKS} - Size: {current_size:,} bytes")

                        # File must be stable for multiple consecutive checks
                        if stable_count >= config.STABILITY_CHECKS:
                            logger.info(f"Recording complete: {file_path.name} ({current_size:,} bytes)")
                            return
                    else:
                        logger.debug(f"File too small: {current_size} bytes (min {config.MIN_FILE_SIZE})")
                else:
                    # Size changed - recording still in progress
                    if stable_count > 0:
                        logger.debug(f"Recording in progress... {current_size:,} bytes")
                    stable_count = 0

                last_size = current_size
                time.sleep(config.STABLE_WAIT_TIME)

            except FileNotFoundError:
                logger.warning(f"File disappeared: {file_path.name}")
                raise
            except Exception as e:
                logger.error(f"Error checking file: {e}")
                raise

        raise TimeoutError(f"Recording did not complete within {timeout}s: {file_path.name}")


class VideoMonitor:
    """Monitors a directory for new video files."""

    def __init__(self, callback):
        """
        Initialize the video monitor.

        Args:
            callback: Function to call when a new video is detected
        """
        self.callback = callback
        self.observer = None
        self.handler = VideoHandler(callback)

    def start(self):
        """Start monitoring the videos directory."""
        logger.info(f"Starting video monitor on: {config.VIDEOS_DIR}")

        # Create observer
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(config.VIDEOS_DIR),
            recursive=False
        )

        # Start observer
        self.observer.start()
        logger.info("Video monitor started successfully")

    def stop(self):
        """Stop monitoring."""
        if self.observer:
            logger.info("Stopping video monitor...")
            self.observer.stop()
            self.observer.join()
            logger.info("Video monitor stopped")

    def run(self):
        """Run the monitor (blocking)."""
        self.start()
        try:
            logger.info("Monitoring for new videos... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()
