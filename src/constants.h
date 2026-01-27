// numchuck constants
// Centralized configuration values for C++ components
//
// NOTE: JavaScript constant in embedded HTML (_web.cpp) cannot reference
// C++ constants and must be updated manually if changed:
//   - WEB_MAX_CONSOLE_LINES (300) - children.length > 300

#ifndef NUMCHUCK_CONSTANTS_H
#define NUMCHUCK_CONSTANTS_H

namespace numchuck {

// Audio defaults
constexpr int DEFAULT_SAMPLE_RATE = 44100;          // Hz
constexpr int DEFAULT_OUTPUT_CHANNELS = 2;          // Stereo
constexpr int DEFAULT_INPUT_CHANNELS = 0;           // No input by default
constexpr int DEFAULT_BUFFER_SIZE = 512;            // Frames per buffer
constexpr int DEFAULT_NUM_BUFFERS = 8;              // Number of audio buffers

// Audio device defaults
constexpr int DEFAULT_DAC_DEVICE = 0;               // Default output device
constexpr int DEFAULT_ADC_DEVICE = 0;               // Default input device

// Timeouts (milliseconds)
constexpr int WINDOWS_AUDIO_SHUTDOWN_WAIT_MS = 100; // Wait for Windows audio threads to exit
constexpr int SERVER_STARTUP_TIMEOUT_SECS = 5;      // Web server startup timeout

// Web server
constexpr int DEFAULT_WEB_PORT = 8080;              // Default HTTP server port
constexpr int WEB_POLL_INTERVAL_MS = 100;           // Mongoose event loop poll interval
constexpr int WEB_MAX_CONSOLE_LINES = 300;          // Max console log entries in web UI

}  // namespace numchuck

#endif  // NUMCHUCK_CONSTANTS_H
