import pytest
from numchuck import _numchuck as numchuck
import os
import tempfile
import time
from pathlib import Path


def normalize_path(path: str) -> str:
    """Normalize path for ChucK (use forward slashes on all platforms)."""
    # ChucK expects forward slashes and can't handle Windows backslashes
    return str(Path(path).resolve()).replace('\\', '/')


def test_compile_from_file():
    """Test compiling ChucK code from a file"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Path to a basic example file (normalize for Windows compatibility)
    example_file = normalize_path(os.path.join(
        os.path.dirname(__file__),
        '../examples/basic/blit2.ck'
    ))

    # Check if file exists
    assert os.path.exists(example_file), f"Example file not found: {example_file}"

    # Compile from file
    success, shred_ids = chuck.compile_file(example_file)
    assert success, "Failed to compile example file"
    assert len(shred_ids) > 0, "No shreds created"

    # Clean up
    chuck.remove_all_shreds()
    chuck.shutdown()


def test_file_with_working_directory():
    """Test that working directory parameter works correctly"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)

    # Set working directory to examples folder (normalize for Windows compatibility)
    examples_dir = normalize_path(os.path.join(os.path.dirname(__file__), '../examples/basic'))
    chuck.set_param_string(numchuck.PARAM_WORKING_DIRECTORY, examples_dir)
    chuck.init()

    # Now we can reference files relative to working directory
    full_path = normalize_path(os.path.join(examples_dir, 'blit2.ck'))
    success, _ = chuck.compile_file(full_path)
    assert success

    chuck.remove_all_shreds()
    chuck.shutdown()


def test_chugin_loading():
    """Test loading and using chugins (lenient - works with static or dynamic)"""
    # Check if Bitcrusher is available (static or dynamic)
    is_available, is_static = _check_chugin_available("Bitcrusher")

    chugins_dir = _get_chugins_dir()

    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)

    # Only set import path if using dynamic chugins
    if not is_static and chugins_dir:
        chuck.set_param_string_list(numchuck.PARAM_IMPORT_PATH_SYSTEM, [chugins_dir])

    chuck.init()

    # Try to use a chugin (Bitcrusher)
    code = '''
    @import "Bitcrusher";
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
        chuck.remove_all_shreds()

    chuck.shutdown()


def test_realtime_file_playback():
    """Test real-time playback of a file"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create a simple test file (use tempfile for cross-platform compatibility)
    test_file = os.path.join(tempfile.gettempdir(), 'test_chuck.ck')
    with open(test_file, 'w') as f:
        f.write('''
SinOsc s => dac;
440 => s.freq;
0.3 => s.gain;
while(true) { 1::samp => now; }
''')

    # Compile and play (normalize path for Windows compatibility)
    success, _ = chuck.compile_file(normalize_path(test_file))
    assert success

    # Start real-time audio
    if numchuck.start_audio(chuck):
        time.sleep(0.1)  # Play briefly
        numchuck.stop_audio()
        numchuck.shutdown_audio()

    # Clean up
    chuck.remove_all_shreds()
    chuck.shutdown()
    os.remove(test_file)


def test_multiple_file_compilation():
    """Test compiling multiple files"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create two simple files (use tempfile for cross-platform compatibility)
    file1 = os.path.join(tempfile.gettempdir(), 'test1.ck')
    file2 = os.path.join(tempfile.gettempdir(), 'test2.ck')

    with open(file1, 'w') as f:
        f.write('SinOsc s1 => dac; 440 => s1.freq; 0.1 => s1.gain; while(true) { 1::samp => now; }')

    with open(file2, 'w') as f:
        f.write('SinOsc s2 => dac; 550 => s2.freq; 0.1 => s2.gain; while(true) { 1::samp => now; }')

    # Compile both (normalize paths for Windows compatibility)
    success1, ids1 = chuck.compile_file(normalize_path(file1))
    success2, ids2 = chuck.compile_file(normalize_path(file2))

    assert success1 and success2
    assert len(ids1) > 0 and len(ids2) > 0
    assert ids1[0] != ids2[0], "Should have different shred IDs"

    # Clean up
    chuck.remove_all_shreds()
    chuck.shutdown()
    os.remove(file1)
    os.remove(file2)


def test_file_with_syntax_error():
    """Test that file with syntax error fails gracefully"""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()

    # Create a file with syntax error (use tempfile for cross-platform compatibility)
    error_file = os.path.join(tempfile.gettempdir(), 'error.ck')
    with open(error_file, 'w') as f:
        f.write('this is not valid chuck code!')

    # Should fail to compile (normalize path for Windows compatibility)
    success, shred_ids = chuck.compile_file(normalize_path(error_file))
    assert not success, "Should fail to compile invalid code"
    assert len(shred_ids) == 0, "Should not create any shreds"

    # Clean up
    chuck.shutdown()
    os.remove(error_file)


def _get_chugins_dir() -> str | None:
    """Return the chugins directory path (bundled or dev), or None if unavailable."""
    # Check bundled chugins in the installed package first
    try:
        import numchuck
        bundled = Path(numchuck.__file__).parent / "chugins"
        if bundled.is_dir() and any(bundled.glob("*.chug")):
            return str(bundled)
    except Exception:
        pass

    # Fall back to dev tree
    dev_dir = os.path.join(os.path.dirname(__file__), '../examples/chugins')
    if os.path.exists(dev_dir):
        chug_files = [f for f in os.listdir(dev_dir) if f.endswith('.chug')]
        if chug_files:
            return os.path.abspath(dev_dir)

    return None


# Helper to check if dynamic chugins are available
def _dynamic_chugins_available():
    """Check if chugins directory exists and has .chug files"""
    return _get_chugins_dir() is not None


def _check_chugin_available(chugin_name: str) -> tuple[bool, bool]:
    """Check if a chugin is available (static or dynamic).

    Returns:
        (is_available, is_static): Whether chugin is available and if it's statically linked
    """
    # First, try without any import path (static linking)
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
    chuck.init()

    code = f'@import "{chugin_name}"; {chugin_name} test;'
    success, _ = chuck.compile_code(code)
    chuck.remove_all_shreds()
    chuck.shutdown()
    if success:
        return (True, True)  # Available via static linking

    # Try with dynamic chugins path
    chugins_dir = _get_chugins_dir()
    if not chugins_dir:
        return (False, False)

    chuck2 = numchuck.ChucK()
    chuck2.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck2.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck2.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
    chuck2.set_param_string_list(numchuck.PARAM_IMPORT_PATH_SYSTEM, [chugins_dir])
    chuck2.init()

    success, _ = chuck2.compile_code(code)
    chuck2.remove_all_shreds()
    chuck2.shutdown()
    if success:
        return (True, False)  # Available via dynamic loading

    return (False, False)


def test_chugin_bitcrusher_strict():
    """Strict test: Bitcrusher chugin must load and produce audio output"""
    import numpy as np

    is_available, is_static = _check_chugin_available("Bitcrusher")
    if not is_available:
        pytest.skip("Bitcrusher chugin not available (neither static nor dynamic)")

    chugins_dir = _get_chugins_dir()

    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
    if not is_static:
        chuck.set_param_string_list(numchuck.PARAM_IMPORT_PATH_SYSTEM, [chugins_dir])
    chuck.init()

    # Code using Bitcrusher chugin
    code = '''
    @import "Bitcrusher";
    SinOsc s => Bitcrusher bc => dac;
    440 => s.freq;
    0.5 => s.gain;
    8 => bc.bits;
    1 => bc.downsampleFactor;
    while(true) { 1::samp => now; }
    '''

    success, shred_ids = chuck.compile_code(code)
    assert success, "Failed to compile code with Bitcrusher chugin"
    assert len(shred_ids) > 0, "No shreds created"

    # Run and verify audio output
    frames = 1024
    input_buf = np.zeros(frames * 2, dtype=np.float32)
    output_buf = np.zeros(frames * 2, dtype=np.float32)
    chuck.run(input_buf, output_buf, frames)

    # Verify non-zero output (audio is being generated)
    max_amplitude = np.max(np.abs(output_buf))
    assert max_amplitude > 0.01, f"Expected audio output, got max amplitude {max_amplitude}"

    chuck.remove_all_shreds()
    chuck.shutdown()


def test_chugin_gverb_strict():
    """Strict test: GVerb chugin must load and process audio"""
    import numpy as np

    is_available, is_static = _check_chugin_available("GVerb")
    if not is_available:
        pytest.skip("GVerb chugin not available (neither static nor dynamic)")

    chugins_dir = _get_chugins_dir()

    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
    if not is_static:
        chuck.set_param_string_list(numchuck.PARAM_IMPORT_PATH_SYSTEM, [chugins_dir])
    chuck.init()

    # Code using GVerb chugin
    code = '''
    @import "GVerb";
    Impulse imp => GVerb rev => dac;
    1.0 => imp.next;
    while(true) { 1::samp => now; }
    '''

    success, shred_ids = chuck.compile_code(code)
    assert success, "Failed to compile code with GVerb chugin"
    assert len(shred_ids) > 0, "No shreds created"

    # Run and verify audio output
    frames = 2048
    input_buf = np.zeros(frames * 2, dtype=np.float32)
    output_buf = np.zeros(frames * 2, dtype=np.float32)
    chuck.run(input_buf, output_buf, frames)

    # GVerb should produce reverb tail from impulse
    max_amplitude = np.max(np.abs(output_buf))
    assert max_amplitude > 0.001, f"Expected reverb output, got max amplitude {max_amplitude}"

    chuck.remove_all_shreds()
    chuck.shutdown()


def test_chugin_convrev_example():
    """Test loading the ConvRev.ck example file that uses ConvRev chugin"""
    import numpy as np

    is_available, is_static = _check_chugin_available("ConvRev")
    if not is_available:
        pytest.skip("ConvRev chugin not available (neither static nor dynamic)")

    chugins_dir = _get_chugins_dir()
    example_file = normalize_path(os.path.join(os.path.dirname(__file__), '../examples/convrev/ConvRev.ck'))
    ir_file = normalize_path(os.path.join(os.path.dirname(__file__), '../examples/convrev/IRs/hagia-sophia.wav'))

    if not os.path.exists(example_file):
        pytest.skip("ConvRev.ck example not found")
    if not os.path.exists(ir_file):
        pytest.skip("IR file not found")

    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
    if not is_static:
        chuck.set_param_string_list(numchuck.PARAM_IMPORT_PATH_SYSTEM, [chugins_dir])

    # Set working directory so me.dir() works correctly
    examples_convrev_dir = normalize_path(os.path.join(os.path.dirname(__file__), '../examples/convrev'))
    chuck.set_param_string(numchuck.PARAM_WORKING_DIRECTORY, examples_convrev_dir)

    chuck.init()

    success, shred_ids = chuck.compile_file(example_file)
    assert success, "Failed to compile ConvRev.ck example"
    assert len(shred_ids) > 0, "No shreds created"

    # Run for a bit and verify audio output
    frames = 4096
    input_buf = np.zeros(frames * 2, dtype=np.float32)
    output_buf = np.zeros(frames * 2, dtype=np.float32)
    chuck.run(input_buf, output_buf, frames)

    # Should produce audio from the convolution reverb
    max_amplitude = np.max(np.abs(output_buf))
    assert max_amplitude > 0.001, f"Expected audio output from ConvRev, got max amplitude {max_amplitude}"

    chuck.remove_all_shreds()
    chuck.shutdown()
