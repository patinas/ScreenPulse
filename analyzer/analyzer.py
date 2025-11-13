"""Video analyzer using Gemini API."""
import logging
import json
from pathlib import Path
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """Analyzes videos using Gemini API to extract step-by-step instructions."""

    def __init__(self):
        """Initialize the Gemini client."""
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it in .env file or environment."
            )
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        logger.info(f"VideoAnalyzer initialized with model: {config.GEMINI_MODEL}")

    def analyze_video(self, video_path: Path) -> dict:
        """Analyze a video file and extract structured information."""
        logger.info(f"Starting analysis of: {video_path.name}")

        try:
            # Upload video file
            logger.info(f"Uploading video to Gemini API...")
            uploaded_file = self.client.files.upload(file=str(video_path))
            logger.info(f"Video uploaded successfully: {uploaded_file.name}")

            # Wait for file to be processed and become ACTIVE
            import time
            max_wait = 120  # 2 minutes max
            wait_time = 0
            while uploaded_file.state.name != "ACTIVE":
                if wait_time >= max_wait:
                    raise TimeoutError(f"File processing timeout after {max_wait}s")
                time.sleep(2)
                wait_time += 2
                uploaded_file = self.client.files.get(name=uploaded_file.name)
                logger.debug(f"Waiting for file processing... State: {uploaded_file.state.name}")

            logger.info(f"File is ACTIVE and ready for analysis")

            # Create prompt for step-by-step extraction
            prompt = """Analyze this video and provide a detailed breakdown in the following JSON format:

{
  "title": "A concise, descriptive title for this video (max 10 words)",
  "summary": "A brief 2-3 sentence summary of what this video demonstrates or teaches",
  "steps": [
    "Step 1: First action shown in the video with specific details",
    "Step 2: Second action with timing and context",
    "... continue for all distinct steps shown"
  ]
}

Important instructions:
- Create a clear, descriptive title that captures the main topic
- The summary should explain the overall purpose or outcome
- Break down EVERY distinct action or step shown in the video
- Include timing references (e.g., "At 0:15...") for important moments
- Be specific about what is clicked, typed, or demonstrated
- Capture both visual actions and any narration/text shown
- Number each step sequentially
- Return ONLY valid JSON, no other text

Analyze the video now:"""

            # Generate content with video and prompt
            logger.info("Requesting analysis from Gemini...")
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[uploaded_file, prompt]
            )

            # Extract and parse response
            result_text = response.text.strip()
            logger.info("Analysis completed successfully")

            # Clean JSON from markdown code blocks if present
            if result_text.startswith("```json"):
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif result_text.startswith("```"):
                result_text = result_text.split("```")[1].split("```")[0].strip()

            # Parse JSON response
            result = json.loads(result_text)

            # Validate required fields
            required_fields = ["title", "summary", "steps"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            if not isinstance(result["steps"], list) or len(result["steps"]) == 0:
                raise ValueError("Steps must be a non-empty list")

            logger.info(f"Extracted {len(result['steps'])} steps from video")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            raise Exception(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise
        finally:
            # Clean up uploaded file
            try:
                if 'uploaded_file' in locals():
                    self.client.files.delete(name=uploaded_file.name)
                    logger.info("Cleaned up uploaded file from Gemini")
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")
