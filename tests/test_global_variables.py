"""
Tests for ChucK global variable management.
"""

import pytest
from numchuck import _numchuck as numchuck
import numpy as np


def run_audio_cycles(chuck, cycles=5):
    """Helper to run audio processing cycles to allow VM to process messages."""
    num_channels = chuck.get_param_int(numchuck.PARAM_OUTPUT_CHANNELS)
    frames = 512
    input_buf = np.zeros(frames * num_channels, dtype=np.float32)
    output_buf = np.zeros(frames * num_channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)


def test_set_get_global_int():
    """Test setting and getting global int variables."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    # Define a global int variable
    code = "global int myInt;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Set the global int
    chuck.set_global_int("myInt", 42)
    run_audio_cycles(chuck)

    # Get the global int via callback
    result = []
    def callback(value):
        result.append(value)

    chuck.get_global_int("myInt", callback)
    run_audio_cycles(chuck)

    assert len(result) == 1
    assert result[0] == 42


def test_set_get_global_float():
    """Test setting and getting global float variables."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global float myFloat;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    chuck.set_global_float("myFloat", 3.14159)
    run_audio_cycles(chuck)

    result = []
    def callback(value):
        result.append(value)

    chuck.get_global_float("myFloat", callback)
    run_audio_cycles(chuck)

    assert len(result) == 1
    assert abs(result[0] - 3.14159) < 0.0001


def test_set_get_global_string():
    """Test setting and getting global string variables."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global string myString;"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    chuck.set_global_string("myString", "hello world")
    run_audio_cycles(chuck)

    result = []
    def callback(value):
        result.append(value)

    chuck.get_global_string("myString", callback)
    run_audio_cycles(chuck)

    assert len(result) == 1
    assert result[0] == "hello world"


def test_set_get_global_int_array():
    """Test setting and getting global int arrays."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global int myArray[0];"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Set entire array
    chuck.set_global_int_array("myArray", [1, 2, 3, 4, 5])
    run_audio_cycles(chuck)

    # Get entire array
    result = []
    def callback(value):
        result.append(value)

    chuck.get_global_int_array("myArray", callback)
    run_audio_cycles(chuck)

    assert len(result) == 1
    assert result[0] == [1, 2, 3, 4, 5]


def test_set_global_int_array_value():
    """Test setting individual int array elements."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = "global int myArray[5];"
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    # Set individual elements
    chuck.set_global_int_array_value("myArray", 0, 10)
    chuck.set_global_int_array_value("myArray", 2, 20)
    chuck.set_global_int_array_value("myArray", 4, 30)
    run_audio_cycles(chuck)

    # Get entire array to verify
    result = []
    chuck.get_global_int_array("myArray", lambda x: result.append(x))
    run_audio_cycles(chuck)

    assert len(result) == 1
    assert result[0][0] == 10
    assert result[0][2] == 20
    assert result[0][4] == 30


def test_get_all_globals():
    """Test getting list of all global variables."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = """
    global int myInt;
    global float myFloat;
    global string myString;
    """
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    globals_list = chuck.get_all_globals()

    # Should have at least our 3 globals
    assert len(globals_list) >= 3

    # Convert to dict for easier checking
    globals_dict = {name: type_str for type_str, name in globals_list}

    assert "myInt" in globals_dict
    assert "myFloat" in globals_dict
    assert "myString" in globals_dict


def test_get_int_array_value():
    """Test reading a single element of a global int array."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = """
    global int myArray[8];
    42 => myArray[3];
    """
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    result = []
    chuck.get_global_int_array_value("myArray", 3, lambda v: result.append(v))
    run_audio_cycles(chuck)

    assert result == [42]


def test_get_float_array_value():
    """Test reading a single element of a global float array."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = """
    global float myArray[8];
    0.25 => myArray[5];
    """
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    result = []
    chuck.get_global_float_array_value("myArray", 5, lambda v: result.append(v))
    run_audio_cycles(chuck)

    assert result == [0.25]


def test_associative_array_roundtrip():
    """Values written by key from Python can be read back by key."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()

    code = """
    global int scores[0];
    global float gains[0];
    7 => scores["from_chuck"];
    0.5 => gains["from_chuck"];
    """
    success, shred_ids = chuck.compile_code(code)
    assert success
    run_audio_cycles(chuck)

    chuck.set_global_associative_int_array_value("scores", "from_python", 99)
    chuck.set_global_associative_float_array_value("gains", "from_python", 1.5)
    run_audio_cycles(chuck)

    ints, floats = [], []
    chuck.get_global_associative_int_array_value(
        "scores", "from_chuck", lambda v: ints.append(v)
    )
    chuck.get_global_associative_int_array_value(
        "scores", "from_python", lambda v: ints.append(v)
    )
    chuck.get_global_associative_float_array_value(
        "gains", "from_chuck", lambda v: floats.append(v)
    )
    chuck.get_global_associative_float_array_value(
        "gains", "from_python", lambda v: floats.append(v)
    )
    run_audio_cycles(chuck)

    assert ints == [7, 99]
    assert floats == [0.5, 1.5]


def test_high_level_array_access():
    """The Chuck wrapper covers whole arrays, elements and associative keys."""
    from numchuck import Chuck

    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    code = """
    global int counts[4];
    global float levels[4];
    global int scores[0];
    global float gains[0];
    """
    assert chuck.compile(code)[0]
    chuck.run(512)

    chuck.set_int_array("counts", [1, 2, 3, 4])
    chuck.set_float_array("levels", [0.1, 0.2, 0.3, 0.4])
    chuck.set_int_array_value("counts", 2, 30)
    chuck.set_float_array_value("levels", 2, 0.75)
    chuck.set_assoc_int("scores", "a", 11)
    chuck.set_assoc_float("gains", "b", 2.5)

    assert chuck.get_int_array("counts") == [1, 2, 30, 4]
    assert chuck.get_float_array("levels")[2] == pytest.approx(0.75)
    assert chuck.get_int_array_value("counts", 2) == 30
    assert chuck.get_float_array_value("levels", 3) == pytest.approx(0.4)
    assert chuck.get_assoc_int("scores", "a") == 11
    assert chuck.get_assoc_float("gains", "b") == pytest.approx(2.5)

    chuck.close()
