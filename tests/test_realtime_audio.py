import pytest
from numchuck import _numchuck as numchuck
import time


def test_realtime_audio():
    """Test real-time audio playback"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Compile audio code
    code = '''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while(true) { 1::samp => now; }
    '''
    success, _ = chuck.compile_code(code)
    assert success

    # Start real-time audio
    audio_started = numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2)
    assert audio_started

    # Check audio info
    info = numchuck.audio_info()
    assert info['sample_rate'] == 44100
    assert info['num_channels_out'] == 2
    assert info['num_channels_in'] == 0
    assert info['buffer_size'] == 512

    # Let it play briefly
    time.sleep(0.1)

    # Stop audio
    numchuck.stop_audio()
    numchuck.shutdown_audio()


def test_audio_without_init_fails():
    """Test that audio fails gracefully without proper init"""
    chuck = numchuck.ChucK()

    # Try to start audio without initializing ChucK
    # Expected: either returns False or raises RuntimeError/OSError
    audio_started = False
    error_raised = False
    try:
        audio_started = numchuck.start_audio(chuck)
        # If it somehow starts, clean up
        if audio_started:
            numchuck.stop_audio()
            numchuck.shutdown_audio()
    except (RuntimeError, OSError):
        error_raised = True

    # Test passes if audio failed to start OR an error was raised
    # (both indicate proper failure handling)
    assert not audio_started or error_raised, (
        "Expected audio to fail without init, but it started successfully"
    )
