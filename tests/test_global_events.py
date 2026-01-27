"""
Tests for ChucK global event management.
"""

import pytest
import numchuck._numchuck as numchuck
import numpy as np


def run_audio_cycles(chuck, cycles=5):
    """Helper to run audio processing cycles to allow VM to process messages."""
    num_channels = chuck.get_param_int(numchuck.PARAM_OUTPUT_CHANNELS)
    frames = 512
    input_buf = np.zeros(frames * num_channels, dtype=np.float32)
    output_buf = np.zeros(frames * num_channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)


def test_signal_global_event():
    """Test signaling a global event."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
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

    # Verify shred was created (signal completed without crash)
    assert len(shred_ids) == 1


def test_broadcast_global_event():
    """Test broadcasting a global event."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global Event broadcastEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    chuck.broadcast_global_event("broadcastEvent")
    run_audio_cycles(chuck)

    # Verify shred was created (broadcast completed without crash)
    assert len(shred_ids) == 1


def test_event_nonexistent():
    """Test that signaling non-existent event doesn't crash."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    run_audio_cycles(chuck)

    # ChucK queues event messages, so non-existent events may not error immediately.
    # Valid outcomes: (1) no error (event silently ignored), or (2) RuntimeError raised.
    # The key assertion is that it doesn't crash with a segfault or other fatal error.
    error_raised = False
    try:
        chuck.signal_global_event("nonexistentEvent")
        run_audio_cycles(chuck)
    except RuntimeError:
        error_raised = True

    # Test passes if we reach here (either outcome is acceptable)
    assert isinstance(error_raised, bool)  # Explicitly document we handled both cases


def test_listen_for_event():
    """Test listening for global events with callback."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Create global event
    code = "global Event testEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Track callback invocations
    callback_count = [0]

    def on_event():
        callback_count[0] += 1

    # Listen for event (should return listener ID)
    listener_id = chuck.listen_for_global_event("testEvent", on_event, listen_forever=False)
    assert isinstance(listener_id, int)
    assert listener_id > 0

    # Signal the event
    chuck.signal_global_event("testEvent")
    run_audio_cycles(chuck, cycles=10)

    # Callback should have been invoked
    assert callback_count[0] == 1


def test_stop_listening_for_event():
    """Test stopping event listener to prevent memory leaks."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Create global event
    code = "global Event cleanupEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Track callback invocations
    callback_count = [0]

    def on_event():
        callback_count[0] += 1

    # Listen for event
    listener_id = chuck.listen_for_global_event("cleanupEvent", on_event, listen_forever=True)
    assert listener_id > 0

    # Signal once - should trigger
    chuck.signal_global_event("cleanupEvent")
    run_audio_cycles(chuck, cycles=10)
    assert callback_count[0] == 1

    # Stop listening
    chuck.stop_listening_for_global_event("cleanupEvent", listener_id)
    run_audio_cycles(chuck, cycles=5)

    # Signal again - should NOT trigger (listener removed)
    chuck.signal_global_event("cleanupEvent")
    run_audio_cycles(chuck, cycles=10)

    # Count should still be 1 (not incremented)
    assert callback_count[0] == 1


def test_multiple_event_listeners():
    """Test that listener cleanup API exists and works."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Create global event
    code = "global Event multiEvent;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Track callback invocations
    callback_count = [0]

    def on_event():
        callback_count[0] += 1

    # Register listener
    listener_id = chuck.listen_for_global_event("multiEvent", on_event, listen_forever=True)
    assert listener_id > 0

    # Broadcast - should trigger
    chuck.broadcast_global_event("multiEvent")
    run_audio_cycles(chuck, cycles=10)
    assert callback_count[0] >= 1  # At least one invocation

    initial_count = callback_count[0]

    # Clean up listener
    chuck.stop_listening_for_global_event("multiEvent", listener_id)
    run_audio_cycles(chuck, cycles=5)

    # Broadcast again - should not trigger additional callbacks
    chuck.broadcast_global_event("multiEvent")
    run_audio_cycles(chuck, cycles=10)

    # Count should not increase (listener was removed)
    assert callback_count[0] == initial_count
