#!/usr/bin/env bash
# ScreenPulse Systemd Service Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="${SCRIPT_DIR}/screenpulse.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "Installing ScreenPulse as a systemd user service..."
echo "=================================================="

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_USER_DIR"

# Update service file with correct paths
TEMP_SERVICE=$(mktemp)
sed "s|/tmp/screenpulse|${SCRIPT_DIR}|g" "$SERVICE_FILE" > "$TEMP_SERVICE"
sed -i "s|User=%u|User=${USER}|g" "$TEMP_SERVICE"

# Copy service file
cp "$TEMP_SERVICE" "${SYSTEMD_USER_DIR}/screenpulse.service"
rm "$TEMP_SERVICE"

echo "Service file installed to: ${SYSTEMD_USER_DIR}/screenpulse.service"

# Reload systemd daemon
systemctl --user daemon-reload

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  systemctl --user start screenpulse    # Start now"
echo "  systemctl --user stop screenpulse     # Stop"
echo "  systemctl --user status screenpulse   # Check status"
echo "  systemctl --user enable screenpulse   # Start on login"
echo "  systemctl --user disable screenpulse  # Don't start on login"
echo ""
echo "Enable lingering to start on boot (even when not logged in):"
echo "  loginctl enable-linger ${USER}"
echo ""
echo "View logs:"
echo "  journalctl --user -u screenpulse -f"
echo ""
