import pychuck
import numpy as np


def test_version():
    """Test that we can get ChucK version"""
    version = pychuck.version()
    assert version is not None
    assert isinstance(version, str)
    assert "chuck" in version.lower() or len(version) > 0


def test_chuck_create():
    """Test creating a ChucK instance"""
    chuck = pychuck.ChucK()
    assert chuck is not None
    assert not chuck.is_init()


def test_chuck_init():
    """Test initializing ChucK"""
    chuck = pychuck.ChucK()

    # Set parameters
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

    # Initialize
    assert chuck.init()
    assert chuck.is_init()

    # Check parameters were set
    assert chuck.get_param_int(pychuck.PARAM_SAMPLE_RATE) == 44100
    assert chuck.get_param_int(pychuck.PARAM_OUTPUT_CHANNELS) == 2


def test_chuck_compile_code():
    """Test compiling ChucK code"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Simple ChucK code that generates a sine wave
    code = '''
    SinOsc s => dac;
    440 => s.freq;
    1::second => now;
    '''

    success, shred_ids = chuck.compile_code(code)
    assert success
    assert len(shred_ids) == 1
    assert shred_ids[0] > 0


def test_chuck_audio_processing():
    """Test running ChucK audio processing"""
    chuck = pychuck.ChucK()
    sample_rate = 44100
    num_channels = 2
    num_frames = 512

    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, sample_rate)
    chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, num_channels)
    chuck.init()

    # Compile simple sine wave generator
    code = '''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    '''
    success, _ = chuck.compile_code(code)
    assert success

    # Process audio
    input_buffer = np.zeros(num_frames * 0, dtype=np.float64)  # No input channels
    output_buffer = np.zeros(num_frames * num_channels, dtype=np.float64)

    chuck.run(input_buffer, output_buffer, num_frames)

    # Check that we got some audio output (should not be all zeros)
    assert output_buffer.any()
    assert np.abs(output_buffer).max() > 0


def test_chuck_now():
    """Test getting current ChucK time"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.init()

    # Initially should be at or near 0
    now = chuck.now()
    assert now >= 0

    # After processing, time should advance
    input_buffer = np.zeros(0, dtype=np.float64)
    output_buffer = np.zeros(512 * 2, dtype=np.float64)
    chuck.run(input_buffer, output_buffer, 512)

    now_after = chuck.now()
    assert now_after > now


def test_parameters():
    """Test parameter constants are defined"""
    assert hasattr(pychuck, 'PARAM_SAMPLE_RATE')
    assert hasattr(pychuck, 'PARAM_INPUT_CHANNELS')
    assert hasattr(pychuck, 'PARAM_OUTPUT_CHANNELS')
    assert pychuck.PARAM_SAMPLE_RATE == "SAMPLE_RATE"
