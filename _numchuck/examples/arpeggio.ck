// Simple arpeggiator
// Plays a C major arpeggio repeatedly

SinOsc s => ADSR env => dac;
env.set(10::ms, 50::ms, 0.5, 100::ms);

// C major arpeggio (MIDI notes)
[60, 64, 67, 72] @=> int notes[];

// Tempo
120.0 => float bpm;
(60.0 / bpm)::second => dur beat;

while (true) {
    for (0 => int i; i < notes.size(); i++) {
        Std.mtof(notes[i]) => s.freq;
        env.keyOn();
        beat / 2 => now;
        env.keyOff();
        beat / 2 => now;
    }
}
