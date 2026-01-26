// Hello World in ChucK
// A simple sine wave that plays for 2 seconds

SinOsc s => dac;

// Set frequency to concert A
440.0 => s.freq;

// Set gain (volume)
0.5 => s.gain;

// Print message
<<< "Hello, ChucK!" >>>;

// Play for 2 seconds
2::second => now;

<<< "Goodbye!" >>>;
