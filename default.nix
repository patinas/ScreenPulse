{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    pynput
  ]);
in
pkgs.mkShell {
  buildInputs = [
    pythonEnv
    pkgs.ffmpeg-full
    pkgs.wf-recorder
  ];

  shellHook = ''
    echo "ScreenPulse Environment Ready!"
    echo "=============================="
    echo "Python: $(python3 --version)"
    echo "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"
    echo ""
    echo "Run: ./screenpulse.py"
    echo ""
  '';
}
