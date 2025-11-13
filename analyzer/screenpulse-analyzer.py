#!/usr/bin/env python3
"""ScreenPulse Analyzer - AI Video Analysis System"""
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import config
from analyzer import VideoAnalyzer
from markdown_generator import MarkdownGenerator
from video_monitor import VideoMonitor

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.BASE_DIR / 'screenpulse-analyzer.log')
    ]
)

logger = logging.getLogger(__name__)


class ScreenPulseAnalyzer:
    def __init__(self):
        self.analyzer = VideoAnalyzer()
        self.markdown_gen = MarkdownGenerator()
        self.monitor = VideoMonitor(self.process_video)

    def process_video(self, video_path: Path):
        logger.info(f"Processing recording: {video_path.name}")
        try:
            logger.info("Step 1/2: Analyzing video with AI...")
            analysis_result = self.analyzer.analyze_video(video_path)

            logger.info("Step 2/2: Generating markdown summary...")
            md_path = self.markdown_gen.generate(analysis_result, video_path=video_path)

            if config.DELETE_AFTER_PROCESSING:
                video_path.unlink()

            logger.info(f"✓ Successfully processed: {video_path.name}")
            logger.info(f"  → Summary: {md_path.name}")
            logger.info(f"  → Title: {analysis_result['title']}")
            logger.info(f"  → Steps: {len(analysis_result['steps'])}")
        except Exception as e:
            logger.error(f"Failed to process {video_path.name}: {e}")

    def run(self):
        logger.info("ScreenPulse Analyzer - AI Video Analysis System")
        logger.info(f"Monitoring: {config.VIDEOS_DIR}")
        self.monitor.run()


if __name__ == "__main__":
    load_dotenv()
    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found!")
        sys.exit(1)
    app = ScreenPulseAnalyzer()
    app.run()
