// LFO modulation example
// Demonstrates low-frequency oscillator controlling pitch

// Carrier oscillator
SinOsc carrier => dac;
0.5 => carrier.gain;

// LFO for pitch modulation
SinOsc lfo => blackhole;
5.0 => lfo.freq;  // 5 Hz modulation rate

// Base frequency
440.0 => float baseFreq;

// Modulation depth in Hz
50.0 => float modDepth;

while (true) {
    // Apply LFO to carrier frequency
    baseFreq + (lfo.last() * modDepth) => carrier.freq;
    1::samp => now;
}
