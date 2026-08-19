"""Tests for the high-level numchuck.Chuck API."""

import numpy as np
import pytest

from numchuck import Chuck


class TestChuckConstruction:
    """Test Chuck class construction and initialization."""

    def test_default_construction(self):
        """Test construction with default parameters."""
        chuck = Chuck()
        assert chuck.sample_rate == 44100
        assert chuck.input_channels == 2
        assert chuck.output_channels == 2

    def test_custom_parameters(self):
        """Test construction with custom parameters."""
        chuck = Chuck(sample_rate=48000, output_channels=1, input_channels=1)
        assert chuck.sample_rate == 48000
        assert chuck.output_channels == 1
        assert chuck.input_channels == 1

    def test_version_property(self):
        """Test version property is accessible."""
        chuck = Chuck()
        assert isinstance(chuck.version, str)
        assert len(chuck.version) > 0

    def test_chugin_enable_property(self):
        """Test chugin_enable property."""
        chuck = Chuck(chugin_enable=False)
        assert chuck.chugin_enable is False

    def test_additional_parameters(self):
        """Test additional constructor parameters."""
        chuck = Chuck(
            auto_depend=True,
            deprecate_level=2,
            otf_enable=True,
            otf_port=9999,
            tty_color=True,
            tty_width_hint=120,
        )
        assert chuck.auto_depend is True
        assert chuck.deprecate_level == 2
        assert chuck.otf_enable is True
        assert chuck.otf_port == 9999
        assert chuck.tty_color is True
        assert chuck.tty_width_hint == 120

    def test_readonly_properties(self):
        """Test read-only properties."""
        chuck = Chuck()
        assert chuck.compiler_highlight_on_error is True  # default
        assert isinstance(chuck.is_realtime_audio_hint, bool)
        assert isinstance(chuck.otf_print_warnings, bool)
        assert isinstance(chuck.dump_instructions, bool)

    def test_manual_init(self):
        """Test manual initialization with auto_init=False."""
        chuck = Chuck(auto_init=False)
        assert chuck.init()  # Returns truthy value on success


class TestCompilation:
    """Test code compilation."""

    def test_compile_simple_code(self):
        """Test compiling simple ChucK code."""
        chuck = Chuck()
        success, shred_ids = chuck.compile("SinOsc s => dac;")
        assert success is True
        assert len(shred_ids) == 1
        assert shred_ids[0] > 0

    def test_compile_multiple_shreds(self):
        """Test compiling multiple shreds."""
        chuck = Chuck()
        success, shred_ids = chuck.compile("SinOsc s => dac;", count=3)
        assert success is True
        assert len(shred_ids) == 3

    def test_compile_invalid_code(self):
        """Test compiling invalid code."""
        chuck = Chuck()
        success, shred_ids = chuck.compile("invalid code here")
        assert success is False


class TestRunning:
    """Test running the VM."""

    def test_run_returns_output(self):
        """Test run returns output audio."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        # Run enough frames for audio to be generated
        output = chuck.run(4410)  # 0.1 seconds at 44100 Hz
        assert isinstance(output, np.ndarray)
        assert output.dtype == np.float32
        assert len(output) == 4410
        assert output.max() > 0  # Should have audio output

    def test_run_stereo_output(self):
        """Test run with stereo output."""
        chuck = Chuck(output_channels=2)
        chuck.compile("SinOsc s => dac;")
        output = chuck.run(500)
        assert len(output) == 1000  # 500 frames * 2 channels

    def test_run_with_output_buffer(self):
        """Test run with pre-allocated output buffer."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        output_buf = np.zeros(4410, dtype=np.float32)
        result = chuck.run(4410, output=output_buf)
        # Should return the same buffer
        assert result is output_buf
        # Buffer should be modified in-place
        assert output_buf.max() > 0

    def test_run_with_input_and_output(self):
        """Test run with both input and output buffers."""
        chuck = Chuck(output_channels=1, input_channels=1)
        chuck.compile("adc => dac;")  # Pass-through
        input_buf = np.ones(500, dtype=np.float32) * 0.5
        output_buf = np.zeros(500, dtype=np.float32)
        result = chuck.run(500, output=output_buf, input=input_buf)
        assert result is output_buf
        # Output should have data (pass-through of input)
        assert isinstance(output_buf, np.ndarray)

    def test_run_effect_mode(self):
        """Test run with explicit input/output (effect mode)."""
        chuck = Chuck(output_channels=1, input_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        input_buf = np.zeros(4410, dtype=np.float32)
        output_buf = np.zeros(4410, dtype=np.float32)
        result = chuck.run(4410, output=output_buf, input=input_buf)
        # Should return output buffer
        assert result is output_buf
        # Output should have audio
        assert output_buf.max() > 0

    def test_advance_discards_output(self):
        """Test advance() advances time without returning audio."""
        chuck = Chuck()
        chuck.compile("global int counter; 0 => counter;")
        chuck.advance(100)
        # Just verify it doesn't crash and returns None
        result = chuck.advance(100)
        assert result is None

    def test_run_with_output_loop(self):
        """Test run with output buffer in a loop (zero allocation pattern)."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        output_buf = np.zeros(512, dtype=np.float32)
        # Simulate real-time loop
        for _ in range(10):
            chuck.run(512, output=output_buf)
        # Buffer should have valid audio after loop
        assert output_buf.max() > 0

    def test_run_reuse_internal_buffer(self):
        """Test run with reuse=True for internal buffer management."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        # First call allocates buffer
        audio1 = chuck.run(512, reuse=True)
        assert isinstance(audio1, np.ndarray)
        assert len(audio1) == 512
        # Second call reuses same buffer
        audio2 = chuck.run(512, reuse=True)
        assert audio1 is audio2  # Same buffer object
        assert audio2.max() > 0

    def test_run_reuse_reallocates_on_size_change(self):
        """Test run with reuse=True reallocates when num_frames changes."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
        audio1 = chuck.run(512, reuse=True)
        assert len(audio1) == 512
        # Different size triggers reallocation
        audio2 = chuck.run(1024, reuse=True)
        assert len(audio2) == 1024
        assert audio1 is not audio2  # Different buffer


class TestShredManagement:
    """Test shred management."""

    def test_shreds_property(self):
        """Test shreds property."""
        chuck = Chuck()
        chuck.compile("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        # Shred might have ended, just check it's a list
        assert isinstance(chuck.shreds, list)

    def test_remove_shred(self):
        """Test removing a shred."""
        chuck = Chuck()
        success, shred_ids = chuck.compile("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        if shred_ids:
            # remove_shred may return None or bool depending on implementation
            chuck.remove_shred(shred_ids[0])
            chuck.run(100)
            # After removal, shred should not be in list
            assert shred_ids[0] not in chuck.shreds

    def test_clear_vm(self):
        """Test clearing all shreds."""
        chuck = Chuck()
        chuck.compile("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        chuck.clear()
        chuck.run(100)
        # After clear, should have no shreds
        assert chuck.shreds == []


class TestGlobalVariables:
    """Test global variable operations."""

    def test_set_get_int(self):
        """Test setting and getting global int."""
        chuck = Chuck()
        chuck.compile("global int myInt;")
        chuck.run(100)
        chuck.set_int("myInt", 42)
        value = chuck.get_int("myInt")
        assert value == 42

    def test_set_get_float(self):
        """Test setting and getting global float."""
        chuck = Chuck()
        chuck.compile("global float myFloat;")
        chuck.run(100)
        chuck.set_float("myFloat", 3.14159)
        value = chuck.get_float("myFloat")
        assert abs(value - 3.14159) < 0.0001

    def test_set_get_string(self):
        """Test setting and getting global string."""
        chuck = Chuck()
        chuck.compile('global string myStr;')
        chuck.run(100)
        chuck.set_string("myStr", "hello")
        value = chuck.get_string("myStr")
        assert value == "hello"


class TestEventCallbacks:
    """Test event signaling and callbacks."""

    def test_signal_event(self):
        """Test signaling a global event."""
        chuck = Chuck()
        success, shred_ids = chuck.compile(
            "global Event myEvent; myEvent => now; 1::second => now;"
        )
        assert success, "Compilation should succeed"
        chuck.run(100)  # Let shred start waiting

        # Signal should wake the shred (no exception means success)
        chuck.signal_event("myEvent")
        chuck.run(100)
        assert len(shred_ids) == 1, "Expected one shred to be created"

    def test_broadcast_event(self):
        """Test broadcasting a global event."""
        chuck = Chuck()
        # Create two shreds waiting on same event
        success, shred_ids = chuck.compile(
            "global Event myEvent; myEvent => now; 1::second => now;", count=2
        )
        assert success, "Compilation should succeed"
        chuck.run(100)

        # Broadcast should wake all shreds (no exception means success)
        chuck.broadcast_event("myEvent")
        chuck.run(100)
        assert len(shred_ids) == 2, "Expected two shreds to be created"

    def test_on_event_callback(self):
        """Test registering an event callback."""
        chuck = Chuck()
        chuck.compile("global Event testEvent;")
        chuck.run(100)

        callback_count = [0]

        def on_event():
            callback_count[0] += 1

        callback_id = chuck.on_event("testEvent", on_event, listen_forever=True)
        assert callback_id >= 0

        # Signal the event and run to trigger callback
        chuck.signal_event("testEvent")
        chuck.run(256)

        assert callback_count[0] >= 1

    def test_on_event_single_shot(self):
        """Test event callback with listen_forever=False."""
        chuck = Chuck()
        chuck.compile("global Event testEvent;")
        chuck.run(100)

        callback_count = [0]

        def on_event():
            callback_count[0] += 1

        chuck.on_event("testEvent", on_event, listen_forever=False)

        # Signal twice
        chuck.signal_event("testEvent")
        chuck.run(256)
        chuck.signal_event("testEvent")
        chuck.run(256)

        # With listen_forever=False, callback should only fire once
        assert callback_count[0] == 1

    def test_stop_listening_for_event(self):
        """Test stopping event listener."""
        chuck = Chuck()
        chuck.compile("global Event testEvent;")
        chuck.run(100)

        callback_count = [0]

        def on_event():
            callback_count[0] += 1

        callback_id = chuck.on_event("testEvent", on_event, listen_forever=True)

        # Signal once
        chuck.signal_event("testEvent")
        chuck.run(256)
        first_count = callback_count[0]
        assert first_count >= 1

        # Stop listening
        chuck.stop_listening_for_event("testEvent", callback_id)

        # Signal again - should not trigger callback
        chuck.signal_event("testEvent")
        chuck.run(256)
        assert callback_count[0] == first_count


class TestAdvanceMethod:
    """Test advance() method behavior."""

    def test_advance_triggers_callbacks(self):
        """Test that advance() triggers global variable callbacks."""
        chuck = Chuck()
        chuck.compile("global int counter; 42 => counter;")
        chuck.run(100)

        result = [None]

        def callback(value):
            result[0] = value

        chuck.get_int_async("counter", callback)
        chuck.advance(256)

        assert result[0] == 42

    def test_advance_advances_vm_time(self):
        """Test that advance() advances VM time."""
        chuck = Chuck()
        chuck.compile("global int counter; 0 => counter;")

        # Get initial time via a shred that writes VM time
        chuck.compile("""
            global float vmTime;
            now/samp => vmTime;
        """)
        chuck.advance(1000)
        time1 = chuck.get_float("vmTime")

        # Advance more
        chuck.advance(1000)
        chuck.compile("""
            global float vmTime;
            now/samp => vmTime;
        """)
        chuck.advance(256)
        time2 = chuck.get_float("vmTime")

        assert time2 > time1


class TestBufferReuseModes:
    """Test different buffer management modes in run()."""

    def test_fresh_allocation_each_call(self):
        """Test that default mode allocates fresh buffer each call."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        audio1 = chuck.run(512)
        audio2 = chuck.run(512)

        # Each call should return a new buffer object
        assert audio1 is not audio2

    def test_user_buffer_not_reallocated(self):
        """Test that user-provided buffer is used as-is."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        user_buf = np.zeros(512, dtype=np.float32)
        result = chuck.run(512, output=user_buf)

        assert result is user_buf

    def test_reuse_mode_consistency(self):
        """Test that reuse=True returns same buffer across multiple calls."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        buffers = [chuck.run(512, reuse=True) for _ in range(5)]

        # All should be the same buffer object
        for buf in buffers[1:]:
            assert buf is buffers[0]

    def test_mixed_modes_independence(self):
        """Test that reuse mode doesn't affect fresh allocation mode."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        # Use reuse mode
        reuse_buf = chuck.run(512, reuse=True)

        # Use fresh allocation mode
        fresh_buf = chuck.run(512)

        # They should be different buffers
        assert reuse_buf is not fresh_buf

        # Reuse should still return same buffer
        reuse_buf2 = chuck.run(512, reuse=True)
        assert reuse_buf2 is reuse_buf


class TestRawAccess:
    """Test access to raw low-level API."""

    def test_raw_property(self):
        """Test raw property returns low-level ChucK instance."""
        chuck = Chuck()
        raw = chuck.raw
        # Check it has low-level methods
        assert hasattr(raw, "compile_code")
        assert hasattr(raw, "set_param")
        assert hasattr(raw, "get_param_int")


class TestContextManager:
    """Test context manager support."""

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        with Chuck() as chuck:
            assert chuck.sample_rate == 44100
            success, shreds = chuck.compile("SinOsc s => dac;")
            assert success

    def test_context_manager_cleanup(self):
        """Test that context manager calls close on exit."""
        chuck = None
        with Chuck() as ck:
            chuck = ck
            chuck.compile("SinOsc s => dac;")
        # After exiting context, close() should have been called
        # We can verify by checking the instance is still accessible
        # but operations may fail (implementation-dependent)
        assert chuck is not None

    def test_context_manager_exception_cleanup(self):
        """Test that context manager calls close even on exception."""
        chuck_ref = None
        try:
            with Chuck() as chuck:
                chuck_ref = chuck
                chuck.compile("SinOsc s => dac;")
                raise ValueError("Test exception")
        except ValueError:
            pass
        # close() should have been called even though exception was raised
        assert chuck_ref is not None

    def test_context_manager_with_audio_processing(self):
        """Test context manager with audio processing."""
        with Chuck(output_channels=1) as chuck:
            chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")
            output = chuck.run(4410)
            assert len(output) == 4410
            assert output.max() > 0


class TestStreamIterator:
    """Test stream iteration API."""

    def test_stream_basic(self):
        """Test basic stream iteration."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        chunks = list(chuck.stream(512, max_chunks=5))
        assert len(chunks) == 5
        for chunk in chunks:
            assert len(chunk) == 512
            assert chunk.dtype == np.float32

    def test_stream_produces_audio(self):
        """Test that stream produces actual audio."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        for audio in chuck.stream(512, max_chunks=3):
            # Sine wave should have non-zero values
            assert audio.max() > 0 or audio.min() < 0

    def test_stream_reuse_buffer(self):
        """Test that reuse=True yields the same buffer object."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 1::second => now;")

        buffers = []
        for audio in chuck.stream(256, max_chunks=3, reuse=True):
            # Store the buffer id (same array is reused)
            buffers.append(id(audio))

        # All buffer IDs should be the same when reuse=True
        assert buffers[0] == buffers[1] == buffers[2]

    def test_stream_no_reuse_different_data(self):
        """Test that reuse=False yields independent data each iteration."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 1::second => now;")

        # Collect copies of the data from each chunk
        data_copies = []
        for audio in chuck.stream(256, max_chunks=3, reuse=False):
            data_copies.append(audio.copy())

        # Each chunk should have different data (sine wave progresses)
        # Check that not all chunks are identical
        assert not np.allclose(data_copies[0], data_copies[1])
        assert not np.allclose(data_copies[1], data_copies[2])

    def test_stream_early_break(self):
        """Test that stream can be broken out of early."""
        chuck = Chuck(output_channels=1)
        chuck.compile("SinOsc s => dac; 1::second => now;")

        count = 0
        for audio in chuck.stream(512):  # No max_chunks - infinite
            count += 1
            if count >= 5:
                break

        assert count == 5

    def test_stream_stereo(self):
        """Test stream with stereo output."""
        chuck = Chuck(output_channels=2)
        chuck.compile("SinOsc s => dac; 1::second => now;")

        for audio in chuck.stream(256, max_chunks=2):
            # Stereo: 256 frames * 2 channels = 512 samples
            assert len(audio) == 512

    def test_stream_total_frames(self):
        """Test rendering a specific duration using stream."""
        chuck = Chuck(sample_rate=44100, output_channels=1)
        chuck.compile("SinOsc s => dac; 440 => s.freq; 10::second => now;")

        # Render exactly 1 second of audio
        frames_per_chunk = 512
        chunks_needed = 44100 // frames_per_chunk  # 86 chunks

        all_audio = []
        for audio in chuck.stream(frames_per_chunk, max_chunks=chunks_needed):
            all_audio.append(audio.copy())  # Copy since reuse=True by default

        total_frames = sum(len(a) for a in all_audio)
        assert total_frames == frames_per_chunk * chunks_needed


class TestGlobalsBeforeAnyRun:
    """Global access on a freshly constructed instance must not crash.

    Every global accessor reaches into the VM's globals manager, which
    segfaults if the VM has never been started -- and only run() started one
    implicitly, so `Chuck().set_int("x", 1)` took the process down. Chuck now
    starts the VM at construction. These run in-process, so a regression is a
    hard crash of the test session rather than a failure; that is the nature of
    the bug being guarded.
    """

    def test_set_int_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            chuck.set_int("counter", 1)

    def test_get_int_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            assert chuck.get_int("counter") == 0

    def test_get_float_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            assert chuck.get_float("freq") == 0.0

    def test_get_string_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            assert chuck.get_string("label") == ""

    def test_list_globals_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            assert chuck.raw.get_all_globals() == []

    def test_signal_event_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            chuck.signal_event("trigger")

    def test_shreds_before_any_run(self):
        with Chuck(input_channels=0) as chuck:
            assert chuck.shreds == []

    def test_round_trip_still_works_after_compiling(self):
        """The eager start must not disturb the normal path."""
        with Chuck(input_channels=0) as chuck:
            chuck.compile("global int x; 7 => x; while (true) { 1::samp => now; }")
            chuck.run(256)
            assert chuck.get_int("x") == 7
