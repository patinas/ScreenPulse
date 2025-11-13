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
        self.callback = callback
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        self._process_video_file(file_path, "created")

    def on_modified(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        self._process_video_file(file_path, "modified")

    def _process_video_file(self, file_path: Path, event_type: str):
        if file_path.suffix.lower() not in config.SUPPORTED_FORMATS:
            logger.debug(f"Ignoring non-video file: {file_path.name}")
            return
        if file_path in self.processing:
            logger.debug(f"Already processing: {file_path.name}")
            return
        logger.info(f"Video {event_type}: {file_path.name}")
        self._wait_for_stable_file(file_path)
        self.processing.add(file_path)
        try:
            self.callback(file_path)
        finally:
            self.processing.discard(file_path)

    def _wait_for_stable_file(self, file_path: Path, timeout: int = 60):
        logger.debug(f"Waiting for recording to complete: {file_path.name}")
        start_time = time.time()
        stable_count = 0
        last_size = -1
        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size
                if current_size == last_size:
                    if current_size >= config.MIN_FILE_SIZE:
                        stable_count += 1
                        if stable_count >= config.STABILITY_CHECKS:
                            logger.info(f"Recording complete: {file_path.name} ({current_size:,} bytes)")
                            return
                else:
                    stable_count = 0
                last_size = current_size
                time.sleep(config.STABLE_WAIT_TIME)
            except FileNotFoundError:
                logger.warning(f"File disappeared: {file_path.name}")
                raise
        raise TimeoutError(f"Recording did not complete within {timeout}s: {file_path.name}")


class VideoMonitor:
    def __init__(self, callback):
        self.callback = callback
        self.observer = None
        self.handler = VideoHandler(callback)

    def start(self):
        logger.info(f"Starting video monitor on: {config.VIDEOS_DIR}")
        self.observer = Observer()
        self.observer.schedule(self.handler, str(config.VIDEOS_DIR), recursive=False)
        self.observer.start()
        logger.info("Video monitor started successfully")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
