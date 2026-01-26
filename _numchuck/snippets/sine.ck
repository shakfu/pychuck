// Basic sine wave oscillator
// A simple 440Hz sine wave with adjustable parameters
//
// Global variables:
//   freq (float): Frequency in Hz (default: 440)
//   gain (float): Volume 0.0-1.0 (default: 0.5)

global float freq;
global float gain;

// Set defaults
440.0 => freq;
0.5 => gain;

// Create oscillator and connect to output
SinOsc osc => dac;

// Main loop - update parameters from globals
while (true) {
    freq => osc.freq;
    gain => osc.gain;
    10::ms => now;
}
