#!/usr/bin/env python3
"""
Offline Audio Rendering

This example demonstrates:
- Rendering ChucK audio to numpy arrays (offline processing)
- Processing audio synchronously without real-time playback
- Analyzing the generated audio data
- Saving to WAV file (optional)
"""

import pychuck
import numpy as np
import matplotlib.pyplot as plt

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# ChucK code: frequency sweep
code = """
SinOsc s => dac;
0.3 => s.gain;

// Sweep from 200Hz to 800Hz over 2 seconds
200.0 => float startFreq;
800.0 => float endFreq;
2.0 => float duration;

now => time start;
while((now - start) / second < duration) {
    // Linear interpolation
    (now - start) / second / duration => float t;
    startFreq + (endFreq - startFreq) * t => s.freq;
    1::samp => now;
}
"""

print("Compiling ChucK code...")
success, shred_ids = chuck.compile_code(code)

if success:
    print(f"✓ Compiled! Shred ID: {shred_ids[0]}")

    # Render 2 seconds of audio offline
    sample_rate = 44100
    duration = 2.0
    num_frames = int(sample_rate * duration)

    print(f"Rendering {duration} seconds of audio ({num_frames} frames)...")

    input_buffer = np.zeros(0, dtype=np.float32)  # No input
    output_buffer = np.zeros(num_frames * 2, dtype=np.float32)  # Stereo output

    # Process audio (synchronous/offline)
    chuck.run(input_buffer, output_buffer, num_frames)

    # Analyze the output
    print(f"\nAudio Statistics:")
    print(f"  Buffer size: {len(output_buffer)} samples")
    print(f"  Min value: {output_buffer.min():.4f}")
    print(f"  Max value: {output_buffer.max():.4f}")
    print(f"  Mean: {output_buffer.mean():.4f}")
    print(f"  RMS: {np.sqrt(np.mean(output_buffer**2)):.4f}")

    # Reshape for stereo (frames, channels)
    stereo = output_buffer.reshape(-1, 2)
    left = stereo[:, 0]
    right = stereo[:, 1]

    print(f"\nChannel info:")
    print(f"  Left channel RMS: {np.sqrt(np.mean(left**2)):.4f}")
    print(f"  Right channel RMS: {np.sqrt(np.mean(right**2)):.4f}")

    # Optional: Plot waveform
    try:
        plt.figure(figsize=(12, 4))
        time_axis = np.arange(len(left)) / sample_rate
        plt.plot(time_axis, left, alpha=0.7, label='Left')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.title('Frequency Sweep: 200Hz to 800Hz')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig('/tmp/pychuck_sweep.png', dpi=100)
        print(f"\n✓ Waveform plot saved to /tmp/pychuck_sweep.png")
    except Exception as e:
        print(f"\nNote: Could not create plot (matplotlib not available or no display): {e}")

    # Optional: Save to WAV file
    try:
        import scipy.io.wavfile as wav
        wav.write('/tmp/pychuck_sweep.wav', sample_rate, stereo)
        print(f"✓ Audio saved to /tmp/pychuck_sweep.wav")
    except ImportError:
        print("Note: scipy not available, skipping WAV export")

    print("\nDone!")
else:
    print("✗ Compilation failed!")
