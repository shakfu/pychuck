#!/usr/bin/env python3
"""
Using Chugins (Bitcrusher Plugin)

This example demonstrates:
- Enabling and loading chugins (ChucK plugins)
- Using the Bitcrusher effect
- Configuring chugin search paths
- Real-time audio processing with effects
"""

import pychuck
import time
import os

# Get path to chugins directory
script_dir = os.path.dirname(os.path.abspath(__file__))
chugins_dir = os.path.join(script_dir, '../../examples/chugins')

print(f"Chugins directory: {chugins_dir}")
print(f"Exists: {os.path.exists(chugins_dir)}")

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

# Enable chugins and set search path
chuck.set_param(pychuck.PARAM_CHUGIN_ENABLE, 1)
chuck.set_param_string(pychuck.PARAM_USER_CHUGINS, chugins_dir)

chuck.init()

# ChucK code using Bitcrusher chugin
code = """
// Generate a sawtooth wave
SawOsc saw => Bitcrusher bc => dac;

// Configure the oscillator
220 => saw.freq;
0.3 => saw.gain;

// Configure bitcrusher for lo-fi effect
4 => bc.bits;           // Reduce bit depth (1-16, lower = more distortion)
2 => bc.downsampleFactor;  // Downsample rate (higher = more aliasing)

// Sweep the bit depth over time
now => time start;
while(true) {
    // Sweep bits from 2 to 12 over 8 seconds
    ((now - start) / second) % 8.0 => float t;
    2 + (10 * t / 8.0) => float bits;
    bits $ int => bc.bits;

    1::samp => now;
}
"""

print("\nCompiling ChucK code with Bitcrusher chugin...")
success, shred_ids = chuck.compile_code(code)

if success:
    print(f"✓ Compilation successful! Shred ID: {shred_ids[0]}")
    print("\nBitcrusher will sweep from 2 to 12 bits over 8 seconds")
    print("  2 bits = very lo-fi, crunchy")
    print("  12 bits = cleaner, less distortion")

    # Start real-time audio
    print("\nStarting audio playback...")
    pychuck.start_audio(chuck)

    # Play for 8 seconds to hear the full sweep
    print("Playing for 8 seconds...")
    for i in range(8):
        time.sleep(1)
        print(f"  {i+1}/8 seconds...")

    # Clean up
    print("\nStopping audio...")
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("Done!")
else:
    print("✗ Compilation failed!")
    print("\nPossible reasons:")
    print("  - Bitcrusher.chug not found in chugins directory")
    print("  - Chugins not built (run 'make build' in project root)")
    print(f"  - Search path: {chugins_dir}")
