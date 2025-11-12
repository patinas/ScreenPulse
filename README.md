# ScreenPulse

Automatic screen recorder that captures your activity when your mouse moves and pauses when you're idle. **Runs in background with persistent reboot support.**

## Features

- **Motion-Triggered Recording**: Automatically starts recording when you move your mouse
- **Smart Pause**: Stops recording after 10 minutes of mouse inactivity
- **Auto-Split**: Automatically splits recordings every 40 minutes to keep file sizes manageable
- **Background Operation**: Runs as a daemon in the background
- **Persistent**: Auto-start on system reboot with systemd
- **Logging**: All activity logged to file
- **Optimized Quality**: 720p recording with h264 compression optimized for small file size and good quality
- **Cross-Platform**: Works on both X11 and Wayland display servers

## Requirements

### Nix (Recommended)

ScreenPulse is designed to work with Nix for dependency management:

```bash
cd /tmp/screenpulse
nix-shell --extra-experimental-features 'nix-command flakes'
```

The `default.nix` and `shell.nix` files provide all necessary dependencies:
- Python 3.11 with pynput
- ffmpeg-full (for X11)
- wf-recorder (for Wayland)

## Quick Start

### Option 1: Control Script (Recommended)

```bash
cd /tmp/screenpulse

# Start in background
./screenpulse-ctl start

# Check status
./screenpulse-ctl status

# View live logs
./screenpulse-ctl logs

# Stop
./screenpulse-ctl stop

# Restart
./screenpulse-ctl restart
```

### Option 2: Direct Daemon Mode

```bash
cd /tmp/screenpulse
nix-shell --extra-experimental-features 'nix-command flakes' --run "./screenpulse.py --daemon"
```

### Option 3: Foreground Mode (for testing)

```bash
cd /tmp/screenpulse
nix-shell --extra-experimental-features 'nix-command flakes' --run "./screenpulse.py"
```

## Persistent Auto-Start on Reboot

To make ScreenPulse start automatically on system boot:

### 1. Install Systemd Service

```bash
cd /tmp/screenpulse
./install-service.sh
```

### 2. Enable and Start Service

```bash
# Enable auto-start on login
systemctl --user enable screenpulse

# Start now
systemctl --user start screenpulse

# Check status
systemctl --user status screenpulse

# View logs
journalctl --user -u screenpulse -f
```

### 3. Enable Lingering (Optional)

To start ScreenPulse on boot even when you're not logged in:

```bash
loginctl enable-linger $USER
```

### Systemd Commands

```bash
systemctl --user start screenpulse     # Start service
systemctl --user stop screenpulse      # Stop service
systemctl --user restart screenpulse   # Restart service
systemctl --user status screenpulse    # Check status
systemctl --user enable screenpulse    # Auto-start on login
systemctl --user disable screenpulse   # Disable auto-start
journalctl --user -u screenpulse -f    # Follow logs
```

## How It Works

1. **Start**: Script runs in background, waiting for mouse movement
2. **Recording**: Move your mouse → recording starts automatically
3. **Pause**: Stop moving mouse for 10 minutes → recording stops
4. **Resume**: Move mouse again → new recording starts
5. **Auto-Split**: After 40 minutes, current recording stops and new one starts (if mouse is active)

## Output

### Recordings
All recordings are saved in `recordings/` with timestamped filenames:
```
recordings/
  recording_20250112_143022.mp4
  recording_20250112_145534.mp4
  ...
```

### Logs
Activity is logged to `screenpulse.log`:
```bash
# View recent activity
tail -f screenpulse.log

# Or use control script
./screenpulse-ctl logs
```

### Process Info
When running as daemon, PID is stored in `screenpulse.pid`

## Configuration

Edit the main() function in `screenpulse.py` to customize:

```python
recorder = ScreenPulse(
    output_dir="recordings",      # Where to save recordings
    log_file="screenpulse.log",   # Log file path
    max_duration=40 * 60,         # Max recording time (40 min)
    idle_timeout=10 * 60,         # Idle time before stopping (10 min)
    resolution="1280x720",        # Recording resolution
    crf=25                        # Quality (18-28: lower = better/larger)
)
```

### Quality Settings (CRF)

- **18-20**: Near lossless, very large files
- **23**: High quality (recommended for important recordings)
- **25**: Good balance (default)
- **28**: Lower quality, smaller files

## File Size Optimization

The script uses several optimizations to keep file sizes small:

- **CRF 25**: Constant Rate Factor for good compression
- **Medium preset**: Balances encoding speed and compression
- **720p max**: Limits resolution to reduce file size
- **h264 codec**: Widely compatible and efficient
- **30 fps**: Smooth playback without excessive frames

Typical file sizes:
- ~50-150 MB per 10 minutes (depending on screen activity)
- Static screens compress better than active screens

## Troubleshooting

### "Recording tool not found"
Install ffmpeg (X11) or wf-recorder (Wayland):
```bash
nix-shell --extra-experimental-features 'nix-command flakes'
```

### Permission errors for recordings folder
```bash
chmod +w recordings/
```

### Mouse detection not working
Add your user to the input group:
```bash
sudo usermod -a -G input $USER
```
Then log out and back in.

### Service not starting on reboot
Enable user lingering:
```bash
loginctl enable-linger $USER
```

### High CPU usage
Try increasing CRF value or using faster preset:
```python
crf=28  # Lower quality, less CPU
```

Or in the ffmpeg command, change preset to 'fast' or 'veryfast'.

### Check if running
```bash
./screenpulse-ctl status
# or
ps aux | grep screenpulse
```

## Manual Control

### Start manually
```bash
./screenpulse-ctl start
```

### Stop manually
```bash
./screenpulse-ctl stop
# or
kill $(cat screenpulse.pid)
```

### View logs in real-time
```bash
./screenpulse-ctl logs
```

## Command Line Options

```bash
./screenpulse.py --help

Options:
  --daemon              Run in background as daemon
  --output-dir DIR      Output directory for recordings (default: recordings)
  --log-file FILE       Log file path (default: screenpulse.log)
  --pid-file FILE       PID file path (default: screenpulse.pid)
```

## File Structure

```
/tmp/screenpulse/
├── screenpulse.py           # Main script
├── screenpulse-ctl          # Control script (start/stop/status)
├── screenpulse.service      # Systemd service file
├── install-service.sh       # Systemd installation script
├── default.nix              # Nix environment (optimized)
├── shell.nix                # Alternative Nix config
├── README.md                # This file
├── screenpulse.pid          # PID file (when running)
├── screenpulse.log          # Log file
└── recordings/              # Output directory
```

## Tips

- **Test first**: Run in foreground mode first to verify everything works
- **Storage**: Make sure you have enough disk space (40 min ≈ 300-600 MB)
- **Privacy**: Be aware of what's being recorded - this captures everything on screen
- **Background**: Use systemd service for persistent background operation
- **Logs**: Monitor `screenpulse.log` to see when recordings start/stop

## License

Free to use and modify.
