#!/usr/bin/env python3
"""Test TTS + audio playback on the Pi. Run with same sudo command as mikabox."""
import subprocess
import tempfile
import os
import wave
import struct
import math

# Generate a simple test WAV (sine wave beep)
def make_beep(path, duration=1.0, freq=440, rate=22050):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for i in range(int(rate * duration)):
            sample = int(16000 * math.sin(2 * math.pi * freq * i / rate))
            wf.writeframes(struct.pack("<h", sample))

# Generate a Piper TTS WAV
def make_piper_wav(path):
    try:
        from piper import PiperVoice
        model_path = os.path.expanduser("~/mikabox/models/en_US-lessac-medium.onnx")
        if not os.path.exists(model_path):
            print("❌ Piper model not found at", model_path)
            return False
        voice = PiperVoice.load(model_path)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            voice.synthesize("Hello! I am Mika, your friendly speaker assistant!", wf)
        print(f"✅ Piper WAV generated: {path} ({os.path.getsize(path)} bytes)")
        return True
    except Exception as e:
        print(f"❌ Piper failed: {e}")
        return False

# Test beep
beep_path = "/tmp/mikabox_test_beep.wav"
make_beep(beep_path)
print(f"\n✅ Test beep generated: {beep_path}")

# Test Piper
piper_path = "/tmp/mikabox_test_piper.wav"
has_piper = make_piper_wav(piper_path)

test_file = piper_path if has_piper else beep_path

# Try each player
players = [
    ("paplay", ["paplay", test_file]),
    ("cvlc", ["cvlc", "--play-and-exit", "--no-repeat", test_file]),
    ("vlc", ["vlc", "--intf", "dummy", "--play-and-exit", test_file]),
    ("aplay", ["aplay", test_file]),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", test_file]),
    ("mpv", ["mpv", "--no-video", test_file]),
    ("mplayer", ["mplayer", test_file]),
]

print(f"\n=== TESTING AUDIO PLAYBACK ({test_file}) ===")
print("Listen for audio after each test...\n")

for name, cmd in players:
    print(f"Testing {name}... ", end="", flush=True)
    try:
        result = subprocess.run(cmd, timeout=10, capture_output=True)
        if result.returncode == 0:
            print(f"✅ Returned OK. Did you hear it?")
        else:
            stderr = result.stderr.decode(errors="ignore")[:100]
            print(f"❌ Failed (exit {result.returncode}): {stderr}")
    except FileNotFoundError:
        print(f"⚠️  Not installed")
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

# Cleanup
os.unlink(beep_path)
if has_piper:
    os.unlink(piper_path)

print("\n✨ Tell me which player worked and I'll update the code!")
