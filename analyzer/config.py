"""Configuration for ScreenPulse video analysis system."""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Directories (can be overridden via environment variables)
# Default to external drive recordings folder
VIDEOS_DIR = Path(os.getenv("SCREENPULSE_VIDEOS_DIR", "/mnt/Recordings"))

# Save markdown files in same directory as videos
SAVE_MD_WITH_VIDEO = True  # If True, MD files go in same folder as video
SUMMARIES_DIR = Path(os.getenv("SCREENPULSE_SUMMARIES_DIR", BASE_DIR / "summaries"))

# Ensure directories exist
VIDEOS_DIR.mkdir(exist_ok=True, parents=True)
if not SAVE_MD_WITH_VIDEO:
    SUMMARIES_DIR.mkdir(exist_ok=True, parents=True)

# Supported video formats
SUPPORTED_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}

# Gemini API settings
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Using latest flash model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Video processing settings
MIN_FILE_SIZE = 1024 * 100  # Minimum file size in bytes (100KB) - ignore tiny files
STABLE_WAIT_TIME = 3  # Seconds to wait for file to be fully written
STABILITY_CHECKS = 3  # Number of consecutive size checks before considering file complete
DELETE_AFTER_PROCESSING = False  # Keep videos after creating markdown summaries

# Logging
LOG_LEVEL = "INFO"
