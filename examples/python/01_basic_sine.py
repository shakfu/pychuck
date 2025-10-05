#!/usr/bin/env python3
"""
Basic Sine Wave - Real-time Playback

This example demonstrates:
- Creating a ChucK instance
- Compiling simple ChucK code (inline)
- Starting real-time audio playback
- Playing audio for a specified duration
"""

import pychuck
import time

# Create and configure ChucK instance
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Simple ChucK code: 440Hz sine wave
code = """
SinOsc s => dac;
440 => s.freq;
0.5 => s.gain;
while(true) { 1::samp => now; }
"""

# Compile and run the code
print("Compiling ChucK code...")
success, shred_ids = chuck.compile_code(code)

if success:
    print(f"✓ Compilation successful! Shred ID: {shred_ids[0]}")

    # Start real-time audio
    print("Starting audio playback...")
    pychuck.start_audio(chuck)

    # Play for 3 seconds
    print("Playing 440Hz sine wave for 3 seconds...")
    time.sleep(3)

    # Clean up
    print("Stopping audio...")
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("Done!")
else:
    print("✗ Compilation failed!")
