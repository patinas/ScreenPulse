# Using ScreenPulse with External Drive

This guide shows how to configure ScreenPulse to save recordings to an external drive.

## Quick Setup

### 1. Find Your External Drive Mount Point

```bash
# List all mounted drives
df -h

# Or look in common locations:
ls /media/$USER/
ls /mnt/
ls /run/media/$USER/
```

Example output:
```
/dev/sdb1  1.0T  100G  900G  10% /media/user/MyDrive
```

Your drive is mounted at: `/media/user/MyDrive`

### 2. Edit Configuration File

```bash
cd /tmp/screenpulse
nano screenpulse.conf
```

Change the `OUTPUT_DIR` line to your external drive:

```bash
# Before:
OUTPUT_DIR="recordings"

# After (examples):
OUTPUT_DIR="/media/user/MyDrive/screenpulse-recordings"
# or
OUTPUT_DIR="/mnt/external/recordings"
# or
OUTPUT_DIR="/run/media/user/MyBackupDrive/screenpulse"
```

### 3. Test Configuration

```bash
./screenpulse-ctl test
```

Expected output:
```
Testing output directory...
  Creating: /media/user/MyDrive/screenpulse-recordings
  ✓ Created successfully
  ✓ Write permission OK
  ✓ Available space: 950GB

All tests passed! Configuration is valid.
```

### 4. Start ScreenPulse

```bash
./screenpulse-ctl start
```

## Full Example Configuration

```bash
# ScreenPulse Configuration File
# /tmp/screenpulse/screenpulse.conf

# External drive path
OUTPUT_DIR="/media/user/MyDrive/screenpulse-recordings"

# Keep logs local for faster access
LOG_FILE="screenpulse.log"
PID_FILE="screenpulse.pid"

# 40 minutes per file (2400 seconds)
MAX_DURATION=2400

# Stop after 10 min of inactivity (600 seconds)
IDLE_TIMEOUT=600

# 720p resolution (smaller files)
RESOLUTION="1280x720"

# Good quality/size balance
CRF=25
```

## Troubleshooting

### Drive Not Mounted

If your drive isn't mounted automatically:

```bash
# List available drives
lsblk

# Mount manually (example)
sudo mount /dev/sdb1 /mnt/external

# Make it auto-mount on boot
sudo nano /etc/fstab
# Add line:
# /dev/sdb1  /mnt/external  ext4  defaults  0  2
```

### Permission Denied

If you can't write to the external drive:

```bash
# Check permissions
ls -ld /media/user/MyDrive

# Fix permissions (if needed)
sudo chown -R $USER:$USER /media/user/MyDrive/screenpulse-recordings
```

### Drive Disconnected While Recording

ScreenPulse will log an error and stop recording. When you reconnect the drive:

```bash
# Check status
./screenpulse-ctl status

# Restart if needed
./screenpulse-ctl restart
```

## Best Practices

### 1. Use Fast Drive for Recording

- **SSD/NVMe**: Best for smooth recording
- **HDD 7200rpm**: Good enough for 720p
- **USB 2.0**: May struggle, use lower resolution
- **USB 3.0+**: Recommended

### 2. Monitor Disk Space

```bash
# Check space regularly
./screenpulse-ctl status

# Or manually:
df -h /media/user/MyDrive
```

### 3. Backup Important Recordings

External drives can fail. Copy important recordings to multiple locations:

```bash
# Copy to cloud storage
rsync -av /media/user/MyDrive/screenpulse-recordings/ ~/Nextcloud/recordings/

# Or to another drive
rsync -av /media/user/MyDrive/screenpulse-recordings/ /backup/recordings/
```

### 4. Network Drive (NAS) Example

```bash
# Mount NAS first
sudo mount -t cifs //192.168.1.100/recordings /mnt/nas \
  -o username=myuser,password=mypass

# Then set in config:
OUTPUT_DIR="/mnt/nas/screenpulse"
```

## Performance Tips

### Lower CPU Usage

```bash
# In screenpulse.conf:

# Use faster preset (bigger files, less CPU)
# Edit screenpulse.py and change preset from 'medium' to 'fast'

# Or use hardware acceleration (if available)
# The script automatically uses h264_vaapi on Wayland
```

### Smaller File Sizes

```bash
# In screenpulse.conf:

# Lower resolution
RESOLUTION="854x480"  # 480p

# Higher CRF (lower quality)
CRF=28

# Shorter segments
MAX_DURATION=1200  # 20 minutes
```

## USB Drive Auto-Mount Example

For systemd service to work with USB drives, you may need:

```bash
# Create udev rule for auto-mount
sudo nano /etc/udev/rules.d/99-usb-mount.rules

# Add:
# ACTION=="add", KERNEL=="sd[a-z][0-9]", SUBSYSTEM=="block", RUN+="/usr/bin/systemctl restart --user screenpulse.service"
```

## Checking Configuration

```bash
# View current config
cat screenpulse.conf

# Test without starting
./screenpulse-ctl test

# Check where recordings are going
./screenpulse-ctl status
```

## Example Directory Structure on External Drive

```
/media/user/MyDrive/
└── screenpulse-recordings/
    ├── recording_20250112_090000.mp4  (1.2 GB)
    ├── recording_20250112_095000.mp4  (980 MB)
    ├── recording_20250112_112000.mp4  (1.1 GB)
    └── ...
```

## Summary

1. Find your drive: `df -h`
2. Edit config: `nano screenpulse.conf`
3. Set path: `OUTPUT_DIR="/path/to/drive/recordings"`
4. Test: `./screenpulse-ctl test`
5. Start: `./screenpulse-ctl start`
