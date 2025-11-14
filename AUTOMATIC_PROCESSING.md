# ScreenPulse Automatic Processing

## Service Status

The **screenpulse-analyzer.service** automatically processes all recorded videos when they finish.

### How It Works

1. **Recording Completes** - ScreenPulse finishes recording (idle timeout or max duration)
2. **File Stabilizes** - Waits for file size to stabilize (3 checks over 9 seconds)
3. **Auto-Processing** - Analyzer service detects the stable file and processes it
4. **MD File Created** - Comprehensive blog-post format markdown file is generated

### Configuration

- **Service**: `screenpulse-analyzer.service`
- **Status**: Enabled (starts on boot)
- **Timeout**: 3000 seconds (50 minutes) - handles longest recordings
- **Format**: Comprehensive blog-post with 1500+ words target
- **API Key**: Loaded from `/home/user/screenpulse/.env`

### Stability Features

✅ **Error Handling** - Service continues running even if one video fails
✅ **Long Recording Support** - 50-minute timeout handles 40-minute max recordings
✅ **Rate Limiting** - Respects Gemini API limits (28 RPM, 190 RPD)
✅ **Automatic Restart** - Service restarts if it crashes

### Monitoring

Check service status:
```bash
systemctl --user status screenpulse-analyzer.service
```

View real-time logs:
```bash
tail -f /home/user/screenpulse/screenpulse.log
```

Check for unprocessed videos:
```bash
cd /home/user/screenpulse && .venv/bin/python process_existing.py
```

### Troubleshooting

If videos aren't being processed automatically:

1. **Check service is running:**
   ```bash
   systemctl --user status screenpulse-analyzer.service
   ```

2. **Restart service:**
   ```bash
   systemctl --user restart screenpulse-analyzer.service
   ```

3. **Check logs for errors:**
   ```bash
   tail -50 /home/user/screenpulse/screenpulse.log
   ```

4. **Manually process backlog:**
   ```bash
   cd /home/user/screenpulse && .venv/bin/python process_existing.py --yes
   ```

## Current Setup Status

✅ Service is running and monitoring `/mnt/Recordings`
✅ New API key configured
✅ Timeout increased to handle long recordings
✅ Error handling prevents service crashes
✅ Comprehensive blog-post format enabled

All future videos will be automatically processed when recording stops!
