#!/usr/bin/env python3
"""
Process existing videos that were not analyzed due to timeout issues.
This script will find all videos without corresponding .md files and process them.
"""
import logging
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

import config
from analyzer import VideoAnalyzer
from markdown_generator import MarkdownGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def find_unprocessed_videos():
    """Find videos that don't have corresponding .md files."""
    unprocessed = []

    for video_path in config.VIDEOS_DIR.glob("*"):
        if video_path.suffix.lower() in config.SUPPORTED_FORMATS:
            # Generate expected markdown filename
            md_filename = video_path.stem + ".md"

            # Also check for timestamp-prefixed versions
            md_files = list(config.VIDEOS_DIR.glob(f"*{video_path.stem.lower()}*.md"))

            if not md_files:
                unprocessed.append(video_path)
                logger.info(f"Found unprocessed: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

    return unprocessed


def process_video(video_path: Path, analyzer: VideoAnalyzer, markdown_gen: MarkdownGenerator):
    """Process a single video."""
    logger.info(f"\nProcessing: {video_path.name}")
    logger.info(f"Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")

    try:
        # Analyze video with Gemini
        logger.info("Analyzing video with Gemini AI...")
        analysis_result = analyzer.analyze_video(video_path)

        # Generate markdown file
        logger.info("Generating markdown summary...")
        md_path = markdown_gen.generate(analysis_result, video_path=video_path)

        logger.info(f"✓ Success! Created: {md_path.name}")
        logger.info(f"  Title: {analysis_result['title']}")
        logger.info(f"  Steps: {len(analysis_result['steps'])}")

        return True

    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False


def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process unprocessed ScreenPulse videos")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not config.GEMINI_API_KEY:
        logger.error("ERROR: GEMINI_API_KEY not found!")
        logger.error("Please set your API key in .env file")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ScreenPulse - Process Existing Videos")
    logger.info("=" * 60)

    # Find unprocessed videos
    logger.info(f"\nScanning: {config.VIDEOS_DIR}")
    unprocessed = find_unprocessed_videos()

    if not unprocessed:
        logger.info("\n✓ All videos have been processed!")
        return

    logger.info(f"\nFound {len(unprocessed)} unprocessed video(s)")

    # Ask for confirmation unless --yes flag is used
    if not args.yes:
        try:
            print("\nProcess these videos? (y/n): ", end="", flush=True)
            response = input().strip().lower()
            if response != 'y':
                logger.info("Cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            logger.info("\nCancelled.")
            return

    # Initialize components
    logger.info("\nInitializing analyzer...")
    analyzer = VideoAnalyzer()
    markdown_gen = MarkdownGenerator()

    # Process each video
    success_count = 0
    fail_count = 0

    for i, video_path in enumerate(unprocessed, 1):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Video {i}/{len(unprocessed)}")
        logger.info(f"{'=' * 60}")

        if process_video(video_path, analyzer, markdown_gen):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Total: {len(unprocessed)}")


if __name__ == "__main__":
    main()
