#!/usr/bin/env python3
"""
MikaBox Mic Test — run this on the Pi to diagnose audio input.
Usage: sudo .venv/bin/python mic_test.py
"""
import struct
import time

try:
    import pyaudio
except ImportError:
    print("ERROR: pyaudio not installed. Run: pip install pyaudio")
    exit(1)

pa = pyaudio.PyAudio()

print("\n=== ALL AUDIO DEVICES ===")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    name = info["name"]
    max_in = info["maxInputChannels"]
    max_out = info["maxOutputChannels"]
    rate = int(info["defaultSampleRate"])
    if max_in > 0:
        print(f"  [{i}] INPUT:  '{name}' (in={max_in}, rate={rate})")
    if max_out > 0:
        print(f"  [{i}] OUTPUT: '{name}' (out={max_out}, rate={rate})")

# Find USB mic
usb_idx = None
usb_rate = None
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info["maxInputChannels"] > 0:
        name = info["name"].lower()
        if "usb" in name or "mic" in name:
            usb_idx = i
            usb_rate = int(info["defaultSampleRate"])
            break

if usb_idx is None:
    print("\n❌ No USB mic found! Trying default input...")
    default = pa.get_default_input_device_info()
    usb_idx = default["index"]
    usb_rate = int(default["defaultSampleRate"])
    print(f"   Using default: [{usb_idx}] '{default['name']}' at {usb_rate} Hz")
else:
    print(f"\n✅ Found USB mic: device [{usb_idx}] at {usb_rate} Hz")

print(f"\n=== RECORDING 5 SECONDS (device {usb_idx}, {usb_rate} Hz) ===")
print("Speak into the mic now!\n")

CHUNK = 1024

try:
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=usb_rate,
        input=True,
        input_device_index=usb_idx,
        frames_per_buffer=CHUNK,
    )
    print("✅ Stream opened successfully!")
except Exception as e:
    print(f"❌ Failed to open stream: {e}")
    pa.terminate()
    exit(1)

start = time.time()
max_rms = 0
samples = 0

while time.time() - start < 5:
    try:
        data = stream.read(CHUNK, exception_on_overflow=False)
        count = len(data) // 2
        shorts = struct.unpack(f"<{count}h", data)
        rms = (sum(s * s for s in shorts) / count) ** 0.5
        max_rms = max(max_rms, rms)
        samples += 1

        # Visual meter
        bar_len = int(rms / 100)
        bar = "█" * min(bar_len, 50)
        print(f"  RMS: {rms:6.0f} | {bar}", end="\r")
    except Exception as e:
        print(f"  Read error: {e}")

stream.stop_stream()
stream.close()
pa.terminate()

print(f"\n\n=== RESULTS ===")
print(f"  Chunks read: {samples}")
print(f"  Max RMS:     {max_rms:.0f}")

if max_rms < 50:
    print("  ❌ No audio detected! Mic may not be working or is muted.")
elif max_rms < 500:
    print("  ⚠️  Very quiet. Try speaking louder or moving closer to mic.")
elif max_rms < 1200:
    print(f"  ⚠️  Detected audio but below trigger threshold (1200). Peak was {max_rms:.0f}.")
    print("     → Lower SPEECH_THRESHOLD in voice_manager.py or speak louder.")
else:
    print(f"  ✅ Audio detected! Peak RMS {max_rms:.0f} is above threshold (1200).")
    print("     → Mic is working fine. The issue is elsewhere.")
