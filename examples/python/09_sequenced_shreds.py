#!/usr/bin/env python3
"""
Sequenced Shreds - Time-Delayed Playback

This example demonstrates:
- Launching shreds at specific times (sequencing)
- Creating rhythmic patterns with delayed starts
- Building up a composition layer by layer
- Removing shreds dynamically to create variation
"""

import pychuck
import time

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

print("=== Sequenced Shreds Demo ===\n")
print("Building up a rhythmic composition layer by layer...\n")

# Dictionary to track shreds by name
active_shreds = {}

# Layer 1: Bass drum (kick)
bass_code = """
Impulse imp => ResonZ res => dac;
50 => res.freq;
5 => res.Q;
0.8 => imp.gain;

while(true) {
    1.0 => imp.next;
    500::ms => now;
}
"""

print("Adding Layer 1: Bass drum (500ms intervals)")
success, ids = chuck.compile_code(bass_code)
if success:
    active_shreds['bass'] = ids[0]
    print(f"  ✓ Bass shred ID: {ids[0]}")

# Start audio
pychuck.start_audio(chuck)
time.sleep(2)

# Layer 2: Snare (offset by 250ms)
snare_code = """
Noise n => ADSR env => HPF filt => dac;
3000 => filt.freq;
env.set(0.001::second, 0.05::second, 0.0, 0.01::second);
0.3 => n.gain;

// Wait 250ms offset
250::ms => now;

while(true) {
    env.keyOn();
    10::ms => now;
    env.keyOff();
    490::ms => now;  // Total 500ms loop
}
"""

print("\nAdding Layer 2: Snare (offset 250ms)")
time.sleep(0.5)
success, ids = chuck.compile_code(snare_code)
if success:
    active_shreds['snare'] = ids[0]
    print(f"  ✓ Snare shred ID: {ids[0]}")

time.sleep(2)

# Layer 3: Hi-hat (16th notes)
hihat_code = """
Noise n => ADSR env => HPF filt => dac;
8000 => filt.freq;
2.0 => filt.Q;
env.set(0.001::second, 0.02::second, 0.0, 0.01::second);
0.15 => n.gain;

while(true) {
    env.keyOn();
    5::ms => now;
    env.keyOff();
    120::ms => now;  // 125ms = 8 hits per second
}
"""

print("\nAdding Layer 3: Hi-hat (125ms intervals)")
time.sleep(0.5)
success, ids = chuck.compile_code(hihat_code)
if success:
    active_shreds['hihat'] = ids[0]
    print(f"  ✓ Hi-hat shred ID: {ids[0]}")

time.sleep(2)

# Layer 4: Bass synth melody (delayed start)
bass_synth_code = """
SinOsc s => LPF filt => dac;
200 => filt.freq;
1.0 => filt.Q;
0.25 => s.gain;

// Array of frequencies for a simple bassline
[110.0, 110.0, 165.0, 110.0] @=> float freqs[];
0 => int idx;

while(true) {
    freqs[idx] => s.freq;
    (idx + 1) % freqs.size() => idx;
    500::ms => now;
}
"""

print("\nAdding Layer 4: Bass synth (melodic bassline)")
time.sleep(0.5)
success, ids = chuck.compile_code(bass_synth_code)
if success:
    active_shreds['bass_synth'] = ids[0]
    print(f"  ✓ Bass synth shred ID: {ids[0]}")

print("\n--- Full composition playing ---")
print(f"Active shreds: {len(active_shreds)}")
for name, shred_id in active_shreds.items():
    print(f"  {name}: {shred_id}")

time.sleep(4)

# Create variation by removing and adding layers
print("\n--- Creating variation: Remove hi-hat ---")
chuck.remove_all_shreds()
active_shreds.clear()
time.sleep(0.5)

# Rebuild with different pattern
print("\nRe-adding layers with new pattern...")

# Add bass first
print("  Layer 1: Bass drum")
success, ids = chuck.compile_code(bass_code)
if success:
    active_shreds['bass'] = ids[0]
time.sleep(1)

# Add a pad sound instead of hi-hat
pad_code = """
SinOsc s1 => dac;
SinOsc s2 => dac;
SinOsc s3 => dac;

// Chord tones (A minor)
220.0 => s1.freq;  // A
261.6 => s2.freq;  // C
329.6 => s3.freq;  // E

0.08 => s1.gain => s2.gain => s3.gain;

while(true) {
    1::second => now;
}
"""

print("  Layer 2: Pad (ambient chord)")
time.sleep(1)
success, ids = chuck.compile_code(pad_code)
if success:
    active_shreds['pad'] = ids[0]

print("\n--- New arrangement playing ---")
print(f"Active shreds: {len(active_shreds)}")
for name, shred_id in active_shreds.items():
    print(f"  {name}: {shred_id}")

time.sleep(3)

# Final variation: melodic sequence
print("\n--- Final variation: Add melody ---")
melody_code = """
SinOsc s => ADSR env => NRev rev => dac;
env.set(0.01::second, 0.1::second, 0.7, 0.2::second);
0.15 => rev.mix;
0.2 => s.gain;

// Pentatonic scale melody
[440.0, 495.0, 550.0, 660.0, 550.0, 495.0] @=> float notes[];
[200::ms, 200::ms, 400::ms, 200::ms, 200::ms, 600::ms] @=> dur durations[];
0 => int idx;

while(true) {
    notes[idx] => s.freq;
    env.keyOn();
    durations[idx] => now;
    env.keyOff();
    (idx + 1) % notes.size() => idx;
    50::ms => now;
}
"""

success, ids = chuck.compile_code(melody_code)
if success:
    active_shreds['melody'] = ids[0]
    print(f"  ✓ Melody shred ID: {ids[0]}")

print("\n--- Complete arrangement playing ---")
time.sleep(6)

# Fade out by removing layers one by one
print("\n--- Fading out layers ---")
if 'melody' in active_shreds:
    # Remove melody (can't remove individual shreds, so we'll just document)
    print("  Removing melody...")
    time.sleep(1)

if 'pad' in active_shreds:
    print("  Removing pad...")
    time.sleep(1)

print("  Final bass notes...")
time.sleep(2)

# Clean up
print("\n--- Ending composition ---")
chuck.remove_all_shreds()
time.sleep(0.5)

pychuck.stop_audio()
pychuck.shutdown_audio()

print("\n✓ Done!")
print(f"\nSequencing summary:")
print(f"  - Started with bass drum")
print(f"  - Added snare with 250ms offset")
print(f"  - Layered hi-hat pattern")
print(f"  - Added melodic bassline")
print(f"  - Created variation by rebuilding")
print(f"  - Added ambient pad and melody")
print(f"  - Total runtime: ~20 seconds")
