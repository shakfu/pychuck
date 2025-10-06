"""
Tests for ChucK shred management and introspection.
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


def test_remove_shred():
    """Test removing a shred by ID."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "while (true) { 100::ms => now; }"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Verify shred is running
    all_ids = chuck.get_all_shred_ids()
    assert shred_ids[0] in all_ids

    # Remove the shred
    chuck.remove_shred(shred_ids[0])
    run_audio_cycles(chuck)

    # Verify shred is gone
    all_ids_after = chuck.get_all_shred_ids()
    assert shred_ids[0] not in all_ids_after


def test_get_all_shred_ids():
    """Test getting all running shred IDs."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Spork 3 shreds
    code = "while (true) { 10::ms => now; }"
    success1, ids1 = chuck.compile_code(code)
    success2, ids2 = chuck.compile_code(code)
    success3, ids3 = chuck.compile_code(code)

    assert all([success1, success2, success3])
    run_audio_cycles(chuck)

    all_ids = chuck.get_all_shred_ids()
    assert len(all_ids) >= 3

    # Clean up
    chuck.remove_all_shreds()


def test_get_shred_info():
    """Test getting detailed shred information."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "1::second => now;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    info = chuck.get_shred_info(shred_ids[0])

    assert info["id"] == shred_ids[0]
    assert "name" in info
    assert "is_running" in info
    assert "is_done" in info


def test_get_shred_info_nonexistent():
    """Test that getting info for non-existent shred raises error."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    with pytest.raises(RuntimeError, match="Shred .* not found"):
        chuck.get_shred_info(99999)


def test_clear_vm():
    """Test clearing the VM."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Spork multiple shreds
    for i in range(3):
        success, ids = chuck.compile_code("while (true) { 10::ms => now; }")
        assert success

    run_audio_cycles(chuck)

    # Verify shreds are running
    all_ids = chuck.get_all_shred_ids()
    assert len(all_ids) >= 3

    # Clear VM
    chuck.clear_vm()
    run_audio_cycles(chuck)

    # All shreds should be gone
    all_ids_after = chuck.get_all_shred_ids()
    assert len(all_ids_after) == 0


def test_reset_shred_id():
    """Test resetting shred ID counter."""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Spork some shreds
    for i in range(3):
        success, ids = chuck.compile_code("1::ms => now;")
        assert success

    run_audio_cycles(chuck, cycles=10)  # Let them finish

    # Clear VM and reset ID
    chuck.clear_vm()
    chuck.reset_shred_id()
    run_audio_cycles(chuck)

    # Next shred should have ID 1
    success, new_ids = chuck.compile_code("1::second => now;")
    assert success
    assert new_ids[0] == 1
