#!/usr/bin/env python3
"""
Load and Play ChucK File

This example demonstrates:
- Loading ChucK code from .ck files
- Using the examples/basic directory
- Real-time playback of external ChucK scripts
"""

import pychuck
import time
import os

# Get the path to the ChucK example file
script_dir = os.path.dirname(os.path.abspath(__file__))
chuck_file = os.path.join(script_dir, '../../examples/basic/blit2.ck')

print(f"Loading ChucK file: {chuck_file}")

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile the ChucK file
print("Compiling...")
success, shred_ids = chuck.compile_file(chuck_file)

if success:
    print(f"✓ Compilation successful! Shred IDs: {shred_ids}")

    # Start real-time audio
    print("Starting audio playback...")
    pychuck.start_audio(chuck)

    # Get audio info
    info = pychuck.audio_info()
    print(f"\nAudio System Info:")
    print(f"  Sample rate: {info['sample_rate']} Hz")
    print(f"  Output channels: {info['num_channels_out']}")
    print(f"  Input channels: {info['num_channels_in']}")
    print(f"  Buffer size: {info['buffer_size']} frames")

    # Play for 5 seconds
    print(f"\nPlaying for 5 seconds...")
    time.sleep(5)

    # Clean up
    print("\nStopping audio...")
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("Done!")
else:
    print(f"✗ Compilation failed!")
    print(f"  Make sure the file exists: {chuck_file}")
