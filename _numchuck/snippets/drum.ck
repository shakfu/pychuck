// Simple drum machine
// Plays a basic 4/4 beat with kick, snare, and hihat
//
// Global variables:
//   bpm (float): Tempo in beats per minute (default: 120)
//   kickgain (float): Kick drum gain 0.0-1.0 (default: 0.8)
//   snaregain (float): Snare gain 0.0-1.0 (default: 0.6)
//   hatgain (float): Hihat gain 0.0-1.0 (default: 0.4)

global float bpm;
global float kickgain;
global float snaregain;
global float hatgain;

// Set defaults
120.0 => bpm;
0.8 => kickgain;
0.6 => snaregain;
0.4 => hatgain;

// Drum sounds using synthesis
// Kick: sine with pitch envelope
SinOsc kick => ADSR kickEnv => dac;
kickEnv.set(1::ms, 100::ms, 0.0, 10::ms);

// Snare: noise + tone
Noise snareNoise => BPF snareFilter => ADSR snareEnv => dac;
SinOsc snareTone => snareEnv;
200.0 => snareTone.freq;
1000.0 => snareFilter.freq;
2.0 => snareFilter.Q;
snareEnv.set(1::ms, 80::ms, 0.0, 10::ms);

// Hihat: filtered noise
Noise hatNoise => HPF hatFilter => ADSR hatEnv => dac;
8000.0 => hatFilter.freq;
hatEnv.set(1::ms, 30::ms, 0.0, 10::ms);

// Beat counter
0 => int beat;

// Main loop
while (true) {
    // Calculate beat duration from BPM
    (60.0 / bpm / 4.0)::second => dur sixteenth;

    // Kick on 1, 5, 9, 13 (quarter notes)
    if (beat % 4 == 0) {
        kickgain => kick.gain;
        150.0 => kick.freq;
        kickEnv.keyOn();
        // Pitch envelope for kick
        spork ~ kickPitch();
    }

    // Snare on 5, 13 (beats 2 and 4)
    if (beat == 4 || beat == 12) {
        snaregain * 0.5 => snareNoise.gain;
        snaregain * 0.3 => snareTone.gain;
        snareEnv.keyOn();
    }

    // Hihat on every other 16th
    if (beat % 2 == 0) {
        hatgain => hatNoise.gain;
        hatEnv.keyOn();
    }

    sixteenth => now;
    (beat + 1) % 16 => beat;
}

// Kick pitch envelope
fun void kickPitch() {
    150.0 => float startPitch;
    50.0 => float endPitch;
    50::ms => dur sweepTime;

    now => time start;
    while (now - start < sweepTime) {
        ((sweepTime - (now - start)) / sweepTime) => float ratio;
        endPitch + (startPitch - endPitch) * ratio => kick.freq;
        1::ms => now;
    }
    endPitch => kick.freq;
}
