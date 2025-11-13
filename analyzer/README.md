# ScreenPulse Analyzer

Automated AI-powered video analysis system that monitors recordings and creates markdown summaries.

## Features

- Real-time video monitoring
- Gemini 2.0 Flash AI analysis
- Step-by-step extraction with timestamps
- Markdown summary generation
- Systemd service integration

## Quick Start

```bash
cd analyzer
cp .env.example .env
# Add your Gemini API key to .env
pip install -r requirements.txt
python screenpulse-analyzer.py
```

## Configuration

Edit `config.py` to customize:
- `VIDEOS_DIR`: Directory to monitor
- `SAVE_MD_WITH_VIDEO`: Save MD files with videos
- `DELETE_AFTER_PROCESSING`: Keep/delete videos after analysis

## Documentation

See main repository README for full setup instructions.
