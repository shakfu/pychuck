"""
Integration tests for numchuck.

These tests verify complete workflows and interactions between components,
testing end-to-end scenarios rather than isolated units.
"""

import pytest
from numchuck import _numchuck as numchuck
import numpy as np
import time
from pathlib import Path
import tempfile


def normalize_path(path: str) -> str:
    """Normalize path for ChucK (use forward slashes on all platforms)."""
    # ChucK expects forward slashes and can't handle Windows backslashes
    return str(Path(path).resolve()).replace('\\', '/')


def init_chuck(sample_rate=44100, input_channels=0, output_channels=2):
    """Helper to initialize ChucK with standard settings."""
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, sample_rate)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, input_channels)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, output_channels)
    chuck.init()
    chuck.start()
    return chuck


def run_audio_cycles(chuck, cycles=5):
    """Helper to run audio processing cycles to allow VM to process messages."""
    num_channels = chuck.get_param_int(numchuck.PARAM_OUTPUT_CHANNELS)
    frames = 512
    input_buf = np.zeros(frames * 0, dtype=np.float32)  # No input channels
    output_buf = np.zeros(frames * num_channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)


class TestLiveCodingWorkflow:
    """Test complete live coding workflows."""

    def test_spork_replace_remove_cycle(self):
        """Test complete edit-spork-replace-remove cycle."""
        chuck = init_chuck()

        # Initial code
        code1 = """
            SinOsc s => dac;
            440 => s.freq;
            0.3 => s.gain;
            while(true) { 100::ms => now; }
        """

        # Spork initial shred
        success, shred_ids = chuck.compile_code(code1)
        assert success
        assert len(shred_ids) == 1
        shred_id = shred_ids[0]

        run_audio_cycles(chuck)

        # Verify shred is running
        all_ids = chuck.get_all_shred_ids()
        assert shred_id in all_ids

        # Get shred info
        info = chuck.get_shred_info(shred_id)
        assert info['id'] == shred_id
        assert info['is_running'] or not info['is_done']

        # Replace with new code
        code2 = """
            SawOsc s => dac;
            220 => s.freq;
            0.2 => s.gain;
            while(true) { 100::ms => now; }
        """

        success2, new_ids = chuck.compile_code(code2)
        assert success2
        new_id = new_ids[0]

        # Remove old shred
        chuck.remove_shred(shred_id)
        run_audio_cycles(chuck)

        # Verify old shred is gone, new shred is running
        all_ids = chuck.get_all_shred_ids()
        assert shred_id not in all_ids
        assert new_id in all_ids

        # Remove the new shred
        chuck.remove_shred(new_id)
        run_audio_cycles(chuck)
        all_ids = chuck.get_all_shred_ids()
        assert new_id not in all_ids

    def test_multiple_shred_management(self):
        """Test managing multiple shreds simultaneously."""
        chuck = init_chuck()

        # Spork multiple shreds
        shred_ids = []
        for freq in [220, 330, 440]:
            code = f"""
                SinOsc s => dac;
                {freq} => s.freq;
                0.1 => s.gain;
                while(true) {{ 100::ms => now; }}
            """
            success, ids = chuck.compile_code(code)
            assert success
            shred_ids.extend(ids)

        run_audio_cycles(chuck)

        # Verify all shreds are running
        assert len(shred_ids) == 3
        all_ids = chuck.get_all_shred_ids()
        for sid in shred_ids:
            assert sid in all_ids

        # Remove middle shred
        chuck.remove_shred(shred_ids[1])
        run_audio_cycles(chuck)
        all_ids = chuck.get_all_shred_ids()
        assert shred_ids[1] not in all_ids
        assert shred_ids[0] in all_ids
        assert shred_ids[2] in all_ids

        # Remove all remaining
        chuck.remove_all_shreds()
        run_audio_cycles(chuck)
        all_ids = chuck.get_all_shred_ids()
        assert len(all_ids) == 0


class TestGlobalCommunication:
    """Test Python-ChucK communication workflows."""

    def test_bidirectional_variable_communication(self):
        """Test setting and getting global variables."""
        chuck = init_chuck()

        # Define global variables
        code = """
            global int counter;
            global float frequency;
            global string message;
        """
        success, _ = chuck.compile_code(code)
        assert success

        run_audio_cycles(chuck)

        # Set from Python
        chuck.set_global_int("counter", 42)
        chuck.set_global_float("frequency", 440.0)
        chuck.set_global_string("message", "hello")

        # Get back to Python
        results = {}

        def get_int(val):
            results['counter'] = val

        def get_float(val):
            results['frequency'] = val

        def get_string(val):
            results['message'] = val

        chuck.get_global_int("counter", get_int)
        chuck.get_global_float("frequency", get_float)
        chuck.get_global_string("message", get_string)

        # Give callbacks time to execute
        run_audio_cycles(chuck, 10)
        time.sleep(0.1)

        assert results['counter'] == 42
        assert results['frequency'] == 440.0
        assert results['message'] == "hello"

    def test_event_driven_workflow(self):
        """Test event-based communication between Python and ChucK."""
        chuck = init_chuck()

        # Define global event
        code = """
            global Event trigger;
        """
        success, _ = chuck.compile_code(code)
        assert success

        run_audio_cycles(chuck)

        # Set up listener
        triggered = []

        def on_trigger():
            triggered.append(time.time())

        listener_id = chuck.listen_for_global_event("trigger", on_trigger, listen_forever=False)
        assert listener_id > 0

        # Signal event from Python
        chuck.signal_global_event("trigger")

        # Give event time to propagate
        run_audio_cycles(chuck, 10)
        time.sleep(0.1)

        # Verify callback was triggered
        assert len(triggered) == 1

    def test_array_manipulation(self):
        """Test array global variable manipulation."""
        chuck = init_chuck()

        # Define array
        code = """
            global int numbers[5];
            global float freqs[3];
        """
        success, _ = chuck.compile_code(code)
        assert success

        run_audio_cycles(chuck)

        # Set entire array
        chuck.set_global_int_array("numbers", [1, 2, 3, 4, 5])
        chuck.set_global_float_array("freqs", [220.0, 440.0, 880.0])

        # Set individual element
        chuck.set_global_int_array_value("numbers", 2, 99)

        # Get back
        results = {}

        def get_ints(val):
            results['numbers'] = val

        def get_floats(val):
            results['freqs'] = val

        chuck.get_global_int_array("numbers", get_ints)
        chuck.get_global_float_array("freqs", get_floats)

        run_audio_cycles(chuck, 10)
        time.sleep(0.1)

        assert results['numbers'] == [1, 2, 99, 4, 5]
        assert results['freqs'] == [220.0, 440.0, 880.0]


class TestAudioProcessingWorkflows:
    """Test complete audio processing workflows."""

    def test_offline_rendering_workflow(self):
        """Test complete offline audio rendering."""
        chuck = init_chuck()

        # Compile audio code
        code = """
            SinOsc s => dac;
            440 => s.freq;
            0.5 => s.gain;
            while(true) { 1::samp => now; }
        """
        success, _ = chuck.compile_code(code)
        assert success

        # Render 1 second of audio
        sample_rate = 44100
        duration = 1.0
        num_frames = int(sample_rate * duration)
        channels = 2

        input_buf = np.zeros(num_frames * 0, dtype=np.float32)
        output_buf = np.zeros(num_frames * channels, dtype=np.float32)

        chuck.run(input_buf, output_buf, num_frames)

        # Verify audio was generated
        assert output_buf.max() > 0.0
        assert output_buf.min() < 0.0
        # Should be roughly within expected gain range
        assert abs(output_buf.max()) < 1.0

    def test_realtime_to_offline_transition(self):
        """Test switching between real-time and offline modes."""
        chuck = init_chuck()

        code = """
            SinOsc s => dac;
            220 => s.freq;
            while(true) { 1::samp => now; }
        """
        success, _ = chuck.compile_code(code)
        assert success

        # Do offline rendering (simulates real-time)
        frames = 1024
        channels = 2
        input_buf = np.zeros(frames * 0, dtype=np.float32)
        output_buf = np.zeros(frames * channels, dtype=np.float32)

        chuck.run(input_buf, output_buf, frames)
        first_output = output_buf.copy()

        # Run again - should continue from where it left off
        chuck.run(input_buf, output_buf, frames)
        second_output = output_buf.copy()

        # Outputs should be different (time advanced)
        assert not np.array_equal(first_output, second_output)


class TestFileWorkflows:
    """Test file-based workflows."""

    def test_compile_and_run_file(self):
        """Test complete file compilation workflow."""
        chuck = init_chuck()

        # Create temporary ChucK file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ck', delete=False) as f:
            f.write("""
                SinOsc s => dac;
                440 => s.freq;
                0.3 => s.gain;
                while(true) { 100::ms => now; }
            """)
            temp_file = f.name

        try:
            # Compile file (normalize path for Windows compatibility)
            success, shred_ids = chuck.compile_file(normalize_path(temp_file))
            assert success
            assert len(shred_ids) > 0

            run_audio_cycles(chuck)

            # Verify shred is running
            info = chuck.get_shred_info(shred_ids[0])
            assert info['is_running'] or not info['is_done']

            # Clean up
            chuck.remove_shred(shred_ids[0])
        finally:
            Path(temp_file).unlink()

    def test_multiple_file_compilation(self):
        """Test compiling multiple interdependent files."""
        chuck = init_chuck()

        # Create multiple temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ck', delete=False) as f1:
            f1.write("""
                // File 1
                SinOsc s1 => dac.left;
                220 => s1.freq;
                while(true) { 100::ms => now; }
            """)
            file1 = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ck', delete=False) as f2:
            f2.write("""
                // File 2
                SinOsc s2 => dac.right;
                440 => s2.freq;
                while(true) { 100::ms => now; }
            """)
            file2 = f2.name

        try:
            # Compile both files (normalize paths for Windows compatibility)
            success1, ids1 = chuck.compile_file(normalize_path(file1))
            success2, ids2 = chuck.compile_file(normalize_path(file2))

            assert success1 and success2
            assert len(ids1) > 0 and len(ids2) > 0

            run_audio_cycles(chuck)

            # Both should be running
            all_ids = chuck.get_all_shred_ids()
            assert ids1[0] in all_ids
            assert ids2[0] in all_ids

            # Clean up
            chuck.remove_all_shreds()
        finally:
            Path(file1).unlink()
            Path(file2).unlink()


class TestVMLifecycle:
    """Test VM lifecycle and state management."""

    def test_init_run_reset_cycle(self):
        """Test complete VM initialization and reset cycle."""
        chuck = numchuck.ChucK()

        # Initial state
        assert not chuck.is_init()

        # Initialize
        chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
        chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
        chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
        chuck.init()
        assert chuck.is_init()

        chuck.start()

        # Compile and run
        success, ids = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success

        run_audio_cycles(chuck)

        # VM should be running
        assert chuck.vm_running()

        # Clear VM
        chuck.clear_vm()
        run_audio_cycles(chuck)
        all_ids = chuck.get_all_shred_ids()
        assert len(all_ids) == 0

        # Reset shred ID counter
        chuck.reset_shred_id()

        # New shred should start from low ID
        success, new_ids = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success
        # After reset, IDs start fresh
        assert new_ids[0] <= 10  # Reasonable low number

    def test_multiple_initialization(self):
        """Test that multiple init calls work correctly."""
        chuck = numchuck.ChucK()

        # First init
        chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
        chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
        chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
        chuck.init()
        assert chuck.is_init()

        chuck.start()

        # Compile something
        success, _ = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success

        run_audio_cycles(chuck)

        # Second init (should work)
        chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 48000)
        chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 1)
        chuck.init()
        assert chuck.is_init()

        chuck.start()

        # Should still be able to compile
        success, _ = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success


class TestErrorRecovery:
    """Test error recovery workflows."""

    def test_compilation_error_recovery(self):
        """Test recovery from compilation errors."""
        chuck = init_chuck()

        # Try to compile invalid code
        success, ids = chuck.compile_code("this is not valid ChucK code!")
        assert not success
        assert len(ids) == 0

        # Should still be able to compile valid code after error
        success, ids = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success
        assert len(ids) > 0

    def test_remove_nonexistent_shred(self):
        """Test that removing nonexistent shred doesn't crash."""
        chuck = init_chuck()

        # Try to remove shred that doesn't exist
        chuck.remove_shred(99999)  # Should not raise exception

        # VM should still work
        success, _ = chuck.compile_code("SinOsc s => dac; while(true) { 100::ms => now; }")
        assert success


class TestConcurrentOperations:
    """Test concurrent operations and stability."""

    def test_rapid_spork_remove_cycle(self):
        """Test rapid sporking and removing of shreds."""
        chuck = init_chuck()

        code = "SinOsc s => dac; 440 => s.freq; while(true) { 100::ms => now; }"

        # Rapidly spork and remove multiple shreds
        for _ in range(10):
            success, ids = chuck.compile_code(code)
            assert success
            run_audio_cycles(chuck, 2)
            for sid in ids:
                chuck.remove_shred(sid)
            run_audio_cycles(chuck, 2)

        # VM should still be stable
        all_ids = chuck.get_all_shred_ids()
        assert len(all_ids) == 0

    def test_multiple_event_listeners(self):
        """Test multiple listeners on same event."""
        chuck = init_chuck()

        code = "global Event e;"
        success, _ = chuck.compile_code(code)
        assert success

        run_audio_cycles(chuck)

        # Register multiple listeners
        counters = [0, 0, 0]

        def make_callback(index):
            def callback():
                counters[index] += 1
            return callback

        listener_ids = []
        for i in range(3):
            lid = chuck.listen_for_global_event("e", make_callback(i), listen_forever=True)
            listener_ids.append(lid)

        # Broadcast event
        chuck.broadcast_global_event("e")
        run_audio_cycles(chuck, 10)
        time.sleep(0.1)

        # All listeners should have been triggered
        assert counters == [1, 1, 1]

        # Clean up
        for lid in listener_ids:
            chuck.stop_listening_for_global_event("e", lid)
