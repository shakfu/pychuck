#!/usr/bin/env python3
"""
Using GVerb Reverb Chugin

This example demonstrates:
- Using the GVerb reverb effect chugin
- Creating spatial audio effects
- Mixing dry and wet signals
"""

import pychuck
import time
import os

# Get path to chugins directory
script_dir = os.path.dirname(os.path.abspath(__file__))
chugins_dir = os.path.join(script_dir, '../../examples/chugins')

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.set_param(pychuck.PARAM_CHUGIN_ENABLE, 1)
chuck.set_param_string(pychuck.PARAM_USER_CHUGINS, chugins_dir)
chuck.init()

# ChucK code using GVerb reverb
code = """
// Impulse generator for percussive sound
Impulse imp => GVerb reverb => dac;

// Configure impulse
0.5 => imp.gain;

// Configure reverb
50.0 => reverb.roomsize;     // Room size in meters (10-300)
5.0 => reverb.revtime;       // Reverb time in seconds
0.5 => reverb.dry;           // Dry signal level (0-1)
0.3 => reverb.early;         // Early reflections level (0-1)
0.4 => reverb.tail;          // Reverb tail level (0-1)

// Trigger impulses rhythmically
while(true) {
    1.0 => imp.next;
    500::ms => now;
}
"""

print("Compiling ChucK code with GVerb chugin...")
success, shred_ids = chuck.compile_code(code)

if success:
    print(f"✓ Compilation successful! Shred ID: {shred_ids[0]}")
    print("\nGVerb Settings:")
    print("  Room size: 50 meters")
    print("  Reverb time: 5 seconds")
    print("  Playing impulses every 500ms")

    print("\nStarting audio playback...")
    pychuck.start_audio(chuck)

    print("Playing reverb demo for 10 seconds...")
    time.sleep(10)

    print("\nStopping audio...")
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("Done!")
else:
    print("✗ Compilation failed!")
    print("\nNote: GVerb.chug must be in the chugins directory")
    print(f"Search path: {chugins_dir}")
