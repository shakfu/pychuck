"""
Test error handling and validation in pychuck.

Tests cover:
- Invalid parameters
- Buffer validation errors
- Initialization errors
- Compilation errors
- Audio system errors
"""

import pytest
import pychuck
import numpy as np


# ============================================================================
# Parameter Validation Tests
# ============================================================================

def test_compile_code_empty_string():
    """Test that compiling empty code raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="Code cannot be empty"):
        chuck.compile_code("")


def test_compile_code_zero_count():
    """Test that count=0 raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    code = "SinOsc s => dac;"
    with pytest.raises(ValueError, match="Count must be at least 1"):
        chuck.compile_code(code, count=0)


def test_compile_file_empty_path():
    """Test that compiling with empty file path raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="File path cannot be empty"):
        chuck.compile_file("")


def test_compile_file_zero_count():
    """Test that count=0 raises ValueError for file compilation"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="Count must be at least 1"):
        chuck.compile_file("test.ck", count=0)


# ============================================================================
# Initialization State Tests
# ============================================================================

def test_compile_code_not_initialized():
    """Test that compiling without init raises RuntimeError"""
    chuck = pychuck.ChucK()

    code = "SinOsc s => dac;"
    with pytest.raises(RuntimeError, match="ChucK instance not initialized"):
        chuck.compile_code(code)


def test_compile_file_not_initialized():
    """Test that compiling file without init raises RuntimeError"""
    chuck = pychuck.ChucK()

    with pytest.raises(RuntimeError, match="ChucK instance not initialized"):
        chuck.compile_file("test.ck")


def test_run_not_initialized():
    """Test that running audio without init raises RuntimeError"""
    chuck = pychuck.ChucK()

    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    with pytest.raises(RuntimeError, match="ChucK instance not initialized"):
        chuck.run(input_buf, output_buf, 512)


def test_start_audio_not_initialized():
    """Test that starting audio without init raises RuntimeError"""
    chuck = pychuck.ChucK()

    with pytest.raises(RuntimeError, match="ChucK instance not initialized"):
        pychuck.start_audio(chuck)


# ============================================================================
# Buffer Validation Tests
# ============================================================================

def test_run_negative_frames():
    """Test that negative num_frames raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    with pytest.raises(ValueError, match="num_frames must be positive"):
        chuck.run(input_buf, output_buf, -100)


def test_run_zero_frames():
    """Test that num_frames=0 raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    with pytest.raises(ValueError, match="num_frames must be positive"):
        chuck.run(input_buf, output_buf, 0)


def test_run_wrong_input_buffer_size():
    """Test that wrong input buffer size raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)  # 2 input channels
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Buffer too small (should be 512 * 2 = 1024)
    input_buf = np.zeros(512, dtype=np.float32)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    with pytest.raises(ValueError, match="input size mismatch"):
        chuck.run(input_buf, output_buf, 512)


def test_run_wrong_output_buffer_size():
    """Test that wrong output buffer size raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    input_buf = np.zeros(0, dtype=np.float32)
    # Buffer too small (should be 512 * 2 = 1024)
    output_buf = np.zeros(512, dtype=np.float32)

    with pytest.raises(ValueError, match="output size mismatch"):
        chuck.run(input_buf, output_buf, 512)


def test_run_wrong_dtype_input():
    """Test that wrong dtype for input is caught by nanobind (implicit cast or error)"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Using float64 instead of float32 - nanobind may auto-convert or raise TypeError
    # Behavior depends on nanobind configuration
    input_buf = np.zeros(512 * 2, dtype=np.float64)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    # Either works (implicit conversion) or raises TypeError
    try:
        chuck.run(input_buf, output_buf, 512)
        # If it worked, nanobind converted it
    except TypeError:
        # Expected: nanobind rejected incompatible type
        pass


def test_run_wrong_dtype_output():
    """Test that wrong dtype for output is caught by nanobind"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    input_buf = np.zeros(0, dtype=np.float32)
    # Using float64 instead of float32
    output_buf = np.zeros(512 * 2, dtype=np.float64)

    # Either works (implicit conversion) or raises TypeError
    try:
        chuck.run(input_buf, output_buf, 512)
        # If it worked, nanobind converted it
    except TypeError:
        # Expected: nanobind rejected incompatible type
        pass


def test_run_multidimensional_input():
    """Test that multidimensional input array is rejected by nanobind"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # 2D array instead of 1D - nanobind should reject at binding level
    input_buf = np.zeros((512, 2), dtype=np.float32)
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    # nanobind enforces ndim=1, so this raises TypeError
    with pytest.raises(TypeError, match="incompatible function arguments"):
        chuck.run(input_buf, output_buf, 512)


def test_run_multidimensional_output():
    """Test that multidimensional output array is rejected by nanobind"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    input_buf = np.zeros(0, dtype=np.float32)
    # 2D array instead of 1D - nanobind should reject at binding level
    output_buf = np.zeros((512, 2), dtype=np.float32)

    # nanobind enforces ndim=1, so this raises TypeError
    with pytest.raises(TypeError, match="incompatible function arguments"):
        chuck.run(input_buf, output_buf, 512)


# ============================================================================
# Audio System Validation Tests
# ============================================================================

def test_start_audio_zero_sample_rate():
    """Test that sample_rate=0 raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="Sample rate must be positive"):
        pychuck.start_audio(chuck, sample_rate=0)


def test_start_audio_zero_channels():
    """Test that zero channels raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="At least one audio channel"):
        pychuck.start_audio(chuck, num_dac_channels=0, num_adc_channels=0)


def test_start_audio_zero_buffer_size():
    """Test that buffer_size=0 raises ValueError"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    with pytest.raises(ValueError, match="Buffer size must be positive"):
        pychuck.start_audio(chuck, buffer_size=0)


# ============================================================================
# Compilation Error Tests
# ============================================================================

def test_compile_invalid_syntax():
    """Test that invalid ChucK syntax returns False"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Invalid ChucK code
    code = "this is not valid chuck syntax!!!"
    success, shred_ids = chuck.compile_code(code)

    assert success is False
    assert len(shred_ids) == 0


def test_compile_nonexistent_file():
    """Test that compiling non-existent file returns False"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    success, shred_ids = chuck.compile_file("/nonexistent/path/to/file.ck")

    assert success is False
    assert len(shred_ids) == 0


def test_compile_undefined_class():
    """Test that using undefined class returns False"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # UndefinedClass doesn't exist
    code = "UndefinedClass obj;"
    success, shred_ids = chuck.compile_code(code)

    assert success is False
    assert len(shred_ids) == 0


def test_compile_type_mismatch():
    """Test that type mismatch returns False"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Type error: can't assign string to int
    code = 'int x; "hello" => x;'
    success, shred_ids = chuck.compile_code(code)

    assert success is False
    assert len(shred_ids) == 0


# ============================================================================
# Edge Cases and Boundary Conditions
# ============================================================================

def test_compile_with_count_multiple():
    """Test compiling with count > 1 creates multiple shreds"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    code = "SinOsc s => dac; 440 => s.freq; while(true) { 1::samp => now; }"
    success, shred_ids = chuck.compile_code(code, count=3)

    assert success is True
    assert len(shred_ids) == 3
    # All shred IDs should be different
    assert len(set(shred_ids)) == 3

    chuck.remove_all_shreds()


def test_large_buffer_processing():
    """Test processing large buffer (stress test)"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    code = '''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while(true) { 1::samp => now; }
    '''
    success, _ = chuck.compile_code(code)
    assert success

    # Process 10 seconds of audio (large buffer)
    num_frames = 44100 * 10
    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(num_frames * 2, dtype=np.float32)

    chuck.run(input_buf, output_buf, num_frames)

    # Verify audio was generated
    assert output_buf.any()
    assert np.abs(output_buf).max() > 0

    chuck.remove_all_shreds()


def test_zero_input_channels_with_input():
    """Test that providing input when channels=0 still validates size"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)  # No input channels
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Providing input data when no input channels configured
    input_buf = np.zeros(512, dtype=np.float32)  # Wrong: should be size 0
    output_buf = np.zeros(512 * 2, dtype=np.float32)

    with pytest.raises(ValueError, match="input size mismatch"):
        chuck.run(input_buf, output_buf, 512)


def test_multiple_init_calls():
    """Test that multiple init calls don't cause issues"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

    # First init succeeds
    result1 = chuck.init()
    assert result1  # Returns 1 (truthy) on success
    assert chuck.is_init()

    # Second init returns 0 (already initialized) but doesn't crash
    result2 = chuck.init()
    assert result2 == 0  # Already initialized
    assert chuck.is_init()  # Still initialized

    # Should still work
    code = "SinOsc s => dac;"
    success, _ = chuck.compile_code(code)
    assert success is True


def test_sequential_compile_and_remove():
    """Test sequential compilation and removal"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    code = "SinOsc s => dac; while(true) { 1::samp => now; }"

    # Compile, remove, compile again
    success1, ids1 = chuck.compile_code(code)
    assert success1

    chuck.remove_all_shreds()

    success2, ids2 = chuck.compile_code(code)
    assert success2

    # Should get new shred IDs
    assert ids1[0] != ids2[0]

    chuck.remove_all_shreds()


# ============================================================================
# Cleanup Tests
# ============================================================================

def test_audio_stop_without_start():
    """Test that stopping audio without starting doesn't crash"""
    # This should not raise any errors
    pychuck.stop_audio()
    pychuck.shutdown_audio()


def test_audio_shutdown_without_start():
    """Test that shutting down audio without starting doesn't crash"""
    # This should not raise any errors
    pychuck.shutdown_audio(msWait=0)
    pychuck.shutdown_audio(msWait=100)
