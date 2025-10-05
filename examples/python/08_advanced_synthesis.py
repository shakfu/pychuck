#!/usr/bin/env python3
"""
Advanced Synthesis - FM and Filtering

This example demonstrates:
- Frequency modulation (FM) synthesis
- Using multiple unit generators (UGens)
- Filtering and envelope shaping
- Complex ChucK code from Python
"""

import pychuck
import time

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Advanced FM synthesis with filtering
code = """
// FM Synthesis Setup
SinOsc carrier => LPF filter => ADSR env => dac;
SinOsc modulator => blackhole;

// Carrier frequency (the main pitch we hear)
440 => carrier.freq;

// Modulator affects carrier frequency
200 => modulator.freq;

// Modulation index controls timbre
500 => float modulationIndex;

// Filter settings
2000 => filter.freq;
2.0 => filter.Q;

// Envelope settings (Attack, Decay, Sustain, Release)
env.set(0.01::second, 0.1::second, 0.5, 0.3::second);

// Connect modulator to carrier frequency
fun void modulate() {
    while(true) {
        440 + (modulator.last() * modulationIndex) => carrier.freq;
        1::samp => now;
    }
}
spork ~ modulate();

// Play notes
fun void playNote(float freq, dur duration) {
    freq => carrier.freq;
    env.keyOn();
    duration => now;
    env.keyOff();
    0.05::second => now;  // Short gap between notes
}

// Play a sequence
while(true) {
    // Play a melodic pattern
    playNote(440, 0.3::second);  // A
    playNote(554, 0.3::second);  // C#
    playNote(659, 0.3::second);  // E
    playNote(880, 0.5::second);  // A (octave)

    0.5::second => now;  // Pause

    // Vary modulation index over time
    (modulationIndex + 100) % 1000 => modulationIndex;
}
"""

print("Compiling advanced FM synthesis patch...")
success, shred_ids = chuck.compile_code(code)

if success:
    print(f"✓ Compilation successful! Shred ID: {shred_ids[0]}")
    print("\nThis patch features:")
    print("  - FM synthesis (frequency modulation)")
    print("  - Low-pass filtering")
    print("  - ADSR envelope")
    print("  - Melodic sequence: A - C# - E - A")
    print("  - Evolving modulation index for changing timbre")

    # Start real-time audio
    print("\nStarting audio playback...")
    pychuck.start_audio(chuck)

    # Play for 15 seconds to hear pattern evolution
    print("Playing for 15 seconds...")
    for i in range(15):
        time.sleep(1)
        print(f"  {i+1}/15 seconds (modulation evolving)...")

    # Clean up
    print("\nStopping audio...")
    pychuck.stop_audio()
    pychuck.shutdown_audio()
    print("Done!")
else:
    print("✗ Compilation failed!")
