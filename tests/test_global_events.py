"""
Tests for ChucK global event management.
"""

import pytest
import pychuck
import numpy as np


def run_audio_cycles(chuck, cycles=5):
    """Helper to run audio processing cycles to allow VM to process messages."""
    num_channels = chuck.get_param_int(pychuck.PARAM_OUTPUT_CHANNELS)
    frames = 512
    input_buf = np.zeros(frames * num_channels, dtype=np.float32)
    output_buf = np.zeros(frames * num_channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)


def test_signal_global_event():
    """Test signaling a global event."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Define a global event
    code = "global Event myEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Signal the event (should not raise exception)
    chuck.signal_global_event("myEvent")
    run_audio_cycles(chuck)

    assert True


def test_broadcast_global_event():
    """Test broadcasting a global event."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global Event broadcastEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    chuck.broadcast_global_event("broadcastEvent")
    run_audio_cycles(chuck)

    assert True


def test_event_nonexistent():
    """Test that signaling non-existent event doesn't crash."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    run_audio_cycles(chuck)

    # ChucK queues event messages, so non-existent events may not error immediately
    # Just verify it doesn't crash
    try:
        chuck.signal_global_event("nonexistentEvent")
        run_audio_cycles(chuck)
    except RuntimeError:
        # It's also valid to raise an error
        pass
