{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    ffmpeg-full
    wf-recorder
    python311
    python311Packages.pynput
    python311Packages.evdev
  ];

  shellHook = ''
    # Preserve Wayland environment variables
    export WAYLAND_DISPLAY=''${WAYLAND_DISPLAY:-wayland-1}
    export XDG_RUNTIME_DIR=''${XDG_RUNTIME_DIR:-/run/user/1000}

    echo "ScreenPulse Development Environment"
    echo "==================================="
    echo ""
    echo "Dependencies installed:"
    echo "  - ffmpeg (for X11 screen recording)"
    echo "  - wf-recorder (for Wayland screen recording)"
    echo "  - Python 3.11 with pynput"
    echo ""
    echo "Run: ./screenpulse.py to start recording"
    echo ""
  '';
}
