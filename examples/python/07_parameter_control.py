#!/usr/bin/env python3
"""
Dynamic Parameter Control

This example demonstrates:
- Configuring ChucK VM parameters
- Checking parameter values
- Using different sample rates
- Working directory configuration
"""

import pychuck
import time

print("=== ChucK Parameter Configuration ===\n")

# Create ChucK instance
chuck = pychuck.ChucK()

# Display ChucK version
print(f"ChucK Version: {pychuck.version()}")
print(f"Int size: {chuck.int_size()} bits")
print(f"Active VMs: {chuck.num_vms()}")
print()

# Configure parameters BEFORE init
print("Setting parameters:")

chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 48000)
print(f"  Sample rate: 48000 Hz")

chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
print(f"  Output channels: 2")

chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
print(f"  Input channels: 0")

chuck.set_param(pychuck.PARAM_VM_HALT, 0)
print(f"  VM halt on error: False")

# Set working directory
import os
chuck_examples = os.path.join(os.path.dirname(__file__), '../../examples/basic')
chuck.set_param_string(pychuck.PARAM_WORKING_DIRECTORY, chuck_examples)
print(f"  Working directory: {chuck_examples}")

# Initialize with these parameters
print("\nInitializing ChucK...")
chuck.init()

# Verify parameters
print("\nVerifying parameters:")
sr = chuck.get_param_int(pychuck.PARAM_SAMPLE_RATE)
out_ch = chuck.get_param_int(pychuck.PARAM_OUTPUT_CHANNELS)
in_ch = chuck.get_param_int(pychuck.PARAM_INPUT_CHANNELS)
wd = chuck.get_param_string(pychuck.PARAM_WORKING_DIRECTORY)

print(f"  Sample rate: {sr} Hz")
print(f"  Output channels: {out_ch}")
print(f"  Input channels: {in_ch}")
print(f"  Working directory: {wd}")

# Check initialization status
print(f"\nInitialized: {bool(chuck.is_init())}")
print(f"VM running: {bool(chuck.vm_running())}")
print(f"Current ChucK time: {chuck.now()} samples")

# Compile and run simple code
code = """
SinOsc s => dac;
440 => s.freq;
0.3 => s.gain;
while(true) { 1::samp => now; }
"""

print("\nCompiling code...")
success, ids = chuck.compile_code(code)

if success:
    print(f"✓ Success! Shred ID: {ids[0]}")

    # Start audio
    print("\nStarting audio at 48kHz sample rate...")
    pychuck.start_audio(chuck, sample_rate=48000)

    # Show audio info
    info = pychuck.audio_info()
    print(f"\nAudio system info:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Play
    print("\nPlaying for 3 seconds...")
    time.sleep(3)

    # Check ChucK time advancement
    final_time = chuck.now()
    expected_samples = 48000 * 3  # 3 seconds at 48kHz
    print(f"\nFinal ChucK time: {final_time} samples")
    print(f"Expected: ~{expected_samples} samples")
    print(f"Difference: {abs(final_time - expected_samples)} samples")

    # Cleanup
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("\nDone!")
else:
    print("✗ Compilation failed!")
