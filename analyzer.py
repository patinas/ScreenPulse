"""Video analyzer using Gemini API."""
import logging
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import deque
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

        # Rate limiting tracking
        self.request_timestamps = deque(maxlen=config.MAX_REQUESTS_PER_MINUTE)
        self.daily_requests = 0
        self.last_request_time = 0

        # Calculate next midnight Pacific Time (API quota resets at midnight PT)
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now_pt = datetime.now(pacific_tz)
        next_midnight_pt = (now_pt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.daily_reset_time = next_midnight_pt

        logger.info(f"VideoAnalyzer initialized with model: {config.GEMINI_MODEL}")
        logger.info(f"Rate limits: {config.MAX_REQUESTS_PER_MINUTE} RPM, {config.MAX_REQUESTS_PER_DAY} RPD")
        logger.info(f"Daily quota resets at: {next_midnight_pt.strftime('%Y-%m-%d %H:%M %Z')} (Pacific Time)")

    def _check_rate_limit(self):
        """
        Check and enforce rate limits before making API requests.
        Waits if necessary to stay within limits.
        """
        now = time.time()
        pacific_tz = ZoneInfo("America/Los_Angeles")
        current_time = datetime.now(pacific_tz)

        # Reset daily counter if needed (at midnight Pacific Time)
        if current_time >= self.daily_reset_time:
            logger.info("Daily rate limit reset (midnight Pacific Time)")
            self.daily_requests = 0
            # Calculate next midnight PT
            next_midnight_pt = (current_time + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            self.daily_reset_time = next_midnight_pt

        # Check daily limit
        if self.daily_requests >= config.MAX_REQUESTS_PER_DAY:
            wait_seconds = (self.daily_reset_time - current_time).total_seconds()
            logger.warning(
                f"Daily rate limit reached ({config.MAX_REQUESTS_PER_DAY} requests). "
                f"Waiting {wait_seconds/3600:.1f} hours until midnight Pacific Time."
            )
            time.sleep(wait_seconds)
            self.daily_requests = 0
            # Recalculate next midnight PT after sleep
            current_time = datetime.now(pacific_tz)
            next_midnight_pt = (current_time + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            self.daily_reset_time = next_midnight_pt

        # Enforce minimum interval between requests
        time_since_last = now - self.last_request_time
        if time_since_last < config.MIN_REQUEST_INTERVAL:
            wait_time = config.MIN_REQUEST_INTERVAL - time_since_last
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s before next request")
            time.sleep(wait_time)
            now = time.time()

        # Track request in sliding window (per-minute limit)
        current_minute = now // 60
        self.request_timestamps = deque(
            [ts for ts in self.request_timestamps if ts // 60 == current_minute],
            maxlen=config.MAX_REQUESTS_PER_MINUTE
        )

        if len(self.request_timestamps) >= config.MAX_REQUESTS_PER_MINUTE:
            oldest = self.request_timestamps[0]
            wait_time = 60 - (now - (oldest // 60 * 60))
            if wait_time > 0:
                logger.warning(f"Per-minute rate limit reached. Waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                now = time.time()

        # Record this request
        self.request_timestamps.append(now)
        self.daily_requests += 1
        self.last_request_time = now

        logger.info(
            f"Rate limit status: {self.daily_requests}/{config.MAX_REQUESTS_PER_DAY} daily, "
            f"{len(self.request_timestamps)}/{config.MAX_REQUESTS_PER_MINUTE} per minute"
        )

    def analyze_video(self, video_path: Path) -> dict:
        """
        Analyze a video file and extract structured information.

        Args:
            video_path: Path to the video file

        Returns:
            dict with keys: title, summary, steps

        Raises:
            Exception: If video analysis fails
        """
        logger.info(f"Starting analysis of: {video_path.name}")

        try:
            # Upload video file
            logger.info(f"Uploading video to Gemini API...")
            uploaded_file = self.client.files.upload(file=str(video_path))
            logger.info(f"Video uploaded successfully: {uploaded_file.name}")

            # Wait for file to be processed and become ACTIVE
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

            # Create prompt for comprehensive blog-style guide
            prompt = """Analyze this video and create a comprehensive, detailed blog-post-style guide following this EXACT structure in JSON format:

{
  "title": "Your Main Title: A Clear, Compelling Promise",
  "subtitle": "A subtitle that expands on the value you are providing the reader",
  "introduction": "Start with a strong hook that identifies a common problem or question your reader has (2-3 sentences). Then clearly promise the outcome: 'By the end of this guide, you will know exactly how to [do the thing] so you can [achieve the benefit].'",
  "steps": [
    "### Step 1: The First Major Point or Action\n\nThis is where you explain the first step using clear, simple language. Keep paragraphs short (2-3 sentences) to make them easy to read on a screen.\n\nUse **bolding** to emphasize the most important **keywords** or **concepts** that you want your reader to remember.\n\n**A. A Key Sub-Point or Action**\n\nIf a step is complex, break it down using sub-headings with lettered points:\n\n- Here is one item to consider.\n- Here is a second item to consider.\n- And a third important detail.\n\n**At 0:45** in the video, you can see [describe what happens at this timestamp].",

    "### Step 2: Moving on to the Next Phase\n\nIntroduce the next part of the process with context.\n\nFor sequential actions within a step, use numbered lists:\n\n1. First, perform this action by [specific details].\n2. Next, configure the [setting/option] to [value].\n3. Then, click on [button/element] located at [position].\n4. Finally, verify that [expected result] appears.\n\n> This is a blockquote. Use it to highlight a **key takeaway** or a powerful insight that you really want to stand out.\n\n**At 2:15**, the terminal displays [describe output]. This indicates [explain significance].",

    "### Step 3: Putting It All Together\n\nHere, you might summarize the process or add a final crucial step that ties everything together.\n\n**Key points to remember:**\n- Point one with specific details\n- Point two with technical specifics\n- Point three with best practices\n\n> **Pro Tip:** [Share an expert insight or time-saving trick discovered in the video]"
  ],
  "conclusion": "## Conclusion: Your Next Move\n\nSummarize the main benefit achieved. You now have a complete framework for [doing the thing shown in the video].\n\nThe most important takeaway is to [reiterate the single most critical message].\n\nWhat's the first [topic/project] you're going to apply this to?"
}

CRITICAL INSTRUCTIONS FOR BLOG-POST FORMAT:

**STRUCTURE:**
- Title must be compelling and promise clear value
- Subtitle expands on the promise (1 sentence)
- Introduction MUST start with a hook identifying a problem, then promise the solution
- Each step uses ### headers (not ##) with descriptive action-oriented titles
- Conclusion summarizes benefits and includes a call-to-action question

**CONTENT DEPTH:**
- Each step should be 4-8 sentences minimum with rich detail
- Include sub-points (A, B, C) for complex steps
- Use numbered lists (1, 2, 3) for sequential actions within steps
- Use bullet lists (-) for non-sequential items/considerations
- Add blockquotes (>) for 2-3 key insights throughout the guide

**FORMATTING:**
- Use **bold** extensively for important keywords, tools, values, settings
- Include `code formatting` for commands, file paths, technical terms
- Add timing references: **At 1:25**, **Around the 3:00 mark**, etc.
- Create visual hierarchy with headers, lists, and blockquotes

**DETAIL REQUIREMENTS:**
- Capture EXACT button labels, menu names, field values shown
- Describe UI elements: "the blue 'Save' button in the top-right corner"
- Include error messages verbatim with `monospace formatting`
- Explain WHY each action is taken, not just WHAT
- Describe visual feedback: loading spinners, success messages, state changes
- Note any troubleshooting or problem-solving shown
- Mention keyboard shortcuts used (e.g., Ctrl+S, Cmd+Enter)

**ENGAGEMENT:**
- Write conversationally as if teaching a friend
- Use "you/your" to address the reader directly
- Add context: "This step is crucial because..."
- Include warnings: "⚠️ Be careful not to..."
- Share insights: "Notice how the interface changes to show..."

**COMPLETENESS:**
- Someone should be able to recreate the ENTIRE workflow from your description
- Include setup requirements if shown at the start
- Note any prerequisites or dependencies mentioned
- Describe the final state/outcome achieved

Return ONLY valid JSON with no other text. Make this guide COMPREHENSIVE and DETAILED - aim for 1500+ words of content across all sections."""

            # Check rate limits before making API request
            self._check_rate_limit()

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

            # Validate required fields for new blog-post format
            required_fields = ["title", "subtitle", "introduction", "steps", "conclusion"]
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
