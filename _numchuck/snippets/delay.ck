// Delay effect with feedback
// Processes audio through a delay line with controllable parameters
//
// Global variables:
//   time_ms (float): Delay time in milliseconds (default: 250)
//   feedback (float): Feedback amount 0.0-0.95 (default: 0.5)
//   mix (float): Wet/dry mix 0.0-1.0 (default: 0.5)
//   gain (float): Input gain 0.0-1.0 (default: 0.5)
//
// Usage: Run this snippet then run another sound source

global float time_ms;
global float feedback;
global float mix;
global float gain;

// Set defaults
250.0 => time_ms;
0.5 => feedback;
0.5 => mix;
0.5 => gain;

// Create delay line (max 2 seconds)
Gain input => Gain dry => dac;
input => DelayL delay => Gain wet => dac;
delay => Gain fb => delay;

// Set initial delay time
(time_ms / 1000.0)::second => delay.delay;
2::second => delay.max;

// Main loop - update parameters
while (true) {
    // Update delay time (smooth to avoid clicks)
    (time_ms / 1000.0)::second => delay.delay;

    // Update feedback (limit to prevent runaway)
    Math.min(feedback, 0.95) => fb.gain;

    // Update wet/dry mix
    (1.0 - mix) => dry.gain;
    mix => wet.gain;

    // Update input gain
    gain => input.gain;

    10::ms => now;
}
