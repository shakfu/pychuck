#!/usr/bin/env python3
"""
Multiple Concurrent Shreds

This example demonstrates:
- Running multiple ChucK shreds (threads) simultaneously
- Creating harmonic relationships
- Managing shred lifecycle
"""

import pychuck
import time

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# ChucK code for a single oscillator
# We'll spawn this multiple times with different frequencies
osc_code = """
SinOsc s => dac;
0.2 => s.gain;  // Lower gain since we'll have multiple
while(true) { 1::samp => now; }
"""

print("Creating harmonic series (fundamental + overtones)...")

# Fundamental frequency
fundamental = 220.0  # A3

# Compile multiple instances with different frequencies
shred_ids = []
frequencies = [
    fundamental,        # Fundamental
    fundamental * 2,    # 1st overtone (octave)
    fundamental * 3,    # 2nd overtone (fifth above octave)
    fundamental * 4,    # 3rd overtone (two octaves)
]

for i, freq in enumerate(frequencies):
    # Create code with specific frequency
    code = f"""
    SinOsc s => dac;
    {freq} => s.freq;
    0.15 => s.gain;
    while(true) {{ 1::samp => now; }}
    """

    success, ids = chuck.compile_code(code)
    if success:
        shred_ids.extend(ids)
        print(f"  ✓ Shred {ids[0]}: {freq:.1f} Hz")
    else:
        print(f"  ✗ Failed to compile oscillator at {freq} Hz")

print(f"\nCreated {len(shred_ids)} shreds")
print(f"Shred IDs: {shred_ids}")

# Start real-time audio
print("\nStarting audio playback...")
pychuck.start_audio(chuck)

# Play for 4 seconds
print("Playing harmonic series for 4 seconds...")
time.sleep(4)

# Remove all shreds
print("\nRemoving all shreds...")
chuck.remove_all_shreds()
time.sleep(0.5)  # Brief silence

# Add a new sound
print("Adding a new shred (880 Hz)...")
code = """
SinOsc s => dac;
880 => s.freq;
0.3 => s.gain;
while(true) { 1::samp => now; }
"""
success, new_ids = chuck.compile_code(code)
if success:
    print(f"  ✓ New shred ID: {new_ids[0]}")

# Play for 2 more seconds
print("Playing new sound for 2 seconds...")
time.sleep(2)

# Clean up
print("\nStopping audio...")
pychuck.stop_audio()
pychuck.shutdown_audio()
print("Done!")
