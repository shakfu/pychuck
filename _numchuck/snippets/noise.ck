// Filtered noise generator
// White noise through a resonant lowpass filter
//
// Global variables:
//   cutoff (float): Filter cutoff frequency in Hz (default: 1000)
//   resonance (float): Filter resonance/Q 0.1-10 (default: 2)
//   gain (float): Output gain 0.0-1.0 (default: 0.5)

global float cutoff;
global float resonance;
global float gain;

// Set defaults
1000.0 => cutoff;
2.0 => resonance;
0.5 => gain;

// Noise source through resonant lowpass
Noise n => LPF filter => dac;

// Main loop - update parameters
while (true) {
    cutoff => filter.freq;
    resonance => filter.Q;
    gain => n.gain;
    10::ms => now;
}
