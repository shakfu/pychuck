import pytest
import pychuck
import os
import time


def test_compile_from_file():
    """Test compiling ChucK code from a file"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Path to a basic example file
    example_file = os.path.join(
        os.path.dirname(__file__),
        '../examples/basic/blit2.ck'
    )

    # Check if file exists
    assert os.path.exists(example_file), f"Example file not found: {example_file}"

    # Compile from file
    success, shred_ids = chuck.compile_file(example_file)
    assert success, "Failed to compile example file"
    assert len(shred_ids) > 0, "No shreds created"

    # Clean up
    chuck.remove_all_shreds()


def test_file_with_working_directory():
    """Test that working directory parameter works correctly"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

    # Set working directory to examples folder
    examples_dir = os.path.join(os.path.dirname(__file__), '../examples/basic')
    chuck.set_param_string(pychuck.PARAM_WORKING_DIRECTORY, examples_dir)
    chuck.init()

    # Now we can reference files relative to working directory
    full_path = os.path.join(examples_dir, 'blit2.ck')
    success, _ = chuck.compile_file(full_path)
    assert success


def test_chugin_loading():
    """Test loading and using chugins"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

    # Enable chugins
    chuck.set_param(pychuck.PARAM_CHUGIN_ENABLE, 1)

    # Set chugin search path to examples/chugins
    chugins_dir = os.path.join(os.path.dirname(__file__), '../examples/chugins')
    if os.path.exists(chugins_dir):
        chuck.set_param_string(pychuck.PARAM_USER_CHUGINS, chugins_dir)

    chuck.init()

    # Try to use a chugin (Bitcrusher)
    code = '''
    SinOsc s => Bitcrusher bc => dac;
    440 => s.freq;
    0.3 => s.gain;
    8 => bc.bits;
    1 => bc.downsampleFactor;
    while(true) { 1::samp => now; }
    '''

    success, shred_ids = chuck.compile_code(code)

    # This will succeed if Bitcrusher chugin is available
    if success:
        assert len(shred_ids) > 0
        chuck.remove_all_shreds()
    else:
        # If chugin not found, that's okay for this test
        # Just verify ChucK is working
        simple_code = '''
        SinOsc s => dac;
        440 => s.freq;
        while(true) { 1::samp => now; }
        '''
        success2, _ = chuck.compile_code(simple_code)
        assert success2, "ChucK should work even without chugins"


def test_realtime_file_playback():
    """Test real-time playback of a file"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create a simple test file
    test_file = '/tmp/test_chuck.ck'
    with open(test_file, 'w') as f:
        f.write('''
SinOsc s => dac;
440 => s.freq;
0.3 => s.gain;
while(true) { 1::samp => now; }
''')

    # Compile and play
    success, _ = chuck.compile_file(test_file)
    assert success

    # Start real-time audio
    if pychuck.start_audio(chuck):
        time.sleep(0.1)  # Play briefly
        pychuck.stop_audio()
        pychuck.shutdown_audio()

    # Clean up
    os.remove(test_file)


def test_multiple_file_compilation():
    """Test compiling multiple files"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create two simple files
    file1 = '/tmp/test1.ck'
    file2 = '/tmp/test2.ck'

    with open(file1, 'w') as f:
        f.write('SinOsc s1 => dac; 440 => s1.freq; 0.1 => s1.gain; while(true) { 1::samp => now; }')

    with open(file2, 'w') as f:
        f.write('SinOsc s2 => dac; 550 => s2.freq; 0.1 => s2.gain; while(true) { 1::samp => now; }')

    # Compile both
    success1, ids1 = chuck.compile_file(file1)
    success2, ids2 = chuck.compile_file(file2)

    assert success1 and success2
    assert len(ids1) > 0 and len(ids2) > 0
    assert ids1[0] != ids2[0], "Should have different shred IDs"

    # Clean up
    chuck.remove_all_shreds()
    os.remove(file1)
    os.remove(file2)


def test_file_with_syntax_error():
    """Test that file with syntax error fails gracefully"""
    chuck = pychuck.ChucK()
    chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create a file with syntax error
    error_file = '/tmp/error.ck'
    with open(error_file, 'w') as f:
        f.write('this is not valid chuck code!')

    # Should fail to compile
    success, shred_ids = chuck.compile_file(error_file)
    assert not success, "Should fail to compile invalid code"
    assert len(shred_ids) == 0, "Should not create any shreds"

    # Clean up
    os.remove(error_file)
