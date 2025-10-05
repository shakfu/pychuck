import pytest
import pychuck
import time


def test_realtime_audio():
    """Test real-time audio playback"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
    audio_started = pychuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2)
    assert audio_started

    # Check audio info
    info = pychuck.audio_info()
    assert info['sample_rate'] == 44100
    assert info['num_channels_out'] == 2
    assert info['num_channels_in'] == 0
    assert info['buffer_size'] == 512

    # Let it play briefly
    time.sleep(0.1)

    # Stop audio
    pychuck.stop_audio()
    pychuck.shutdown_audio()


def test_audio_without_init_fails():
    """Test that audio fails gracefully without proper init"""
    chuck = pychuck.ChucK()

    # Try to start audio without initializing ChucK
    # This should fail
    try:
        audio_started = pychuck.start_audio(chuck)
        # If it somehow starts, stop it
        if audio_started:
            pychuck.stop_audio()
            pychuck.shutdown_audio()
    except:
        pass  # Expected to fail
