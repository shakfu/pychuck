// FM synthesis example
// Two-operator FM with controllable parameters
//
// Global variables:
//   carrier (float): Carrier frequency in Hz (default: 220)
//   modfreq (float): Modulator frequency in Hz (default: 110)
//   modindex (float): Modulation index 0-10 (default: 2)
//   gain (float): Output gain 0.0-1.0 (default: 0.5)

global float carrier;
global float modfreq;
global float modindex;
global float gain;

// Set defaults
220.0 => carrier;
110.0 => modfreq;
2.0 => modindex;
0.5 => gain;

// FM synthesis: modulator -> carrier
SinOsc mod => blackhole;
SinOsc car => dac;

// Main loop
while (true) {
    // Update modulator
    modfreq => mod.freq;

    // FM: carrier freq = carrier + (mod * index * carrier)
    carrier + (mod.last() * modindex * carrier) => car.freq;
    gain => car.gain;

    1::samp => now;
}
