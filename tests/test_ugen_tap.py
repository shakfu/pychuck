"""
Tests for reading samples from global UGens (the "tap" facility).
"""

import gc
import time

import numpy as np
import pytest

from numchuck import Chuck
from numchuck import _numchuck as numchuck


TAP_CODE = """
global Gain tap;
tap.buffered(1);
SinOsc s => tap => dac;
440 => s.freq;
1.0 => s.gain;
10::second => now;
"""


def make_chuck(output_channels=2):
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, output_channels)
    chuck.init()
    chuck.start()
    return chuck


def require_audible_tap(chuck, name, timeout=3.0):
    """Skip unless the audio thread is actually producing samples.

    start_audio() returning True only means a device opened. On CI that device
    is a PulseAudio null sink, which opens and then delivers silence -- and
    silence is indistinguishable from a working tap for any assertion phrased
    as "no discontinuities", because np.diff of an all-zero buffer is all
    zeros. Rather than let these tests pass vacuously, wait for real signal and
    skip loudly if none arrives.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        samples = chuck.get_ugen_samples(name, 1024)
        if np.any(samples != 0.0):
            return
        time.sleep(0.05)
    pytest.skip(
        f"audio device opened but produced no samples within {timeout}s "
        f"(tap '{name}' is all zeros); the tap tests cannot be verified here"
    )


def run_frames(chuck, frames=512, cycles=2):
    channels = chuck.get_param_int(numchuck.PARAM_OUTPUT_CHANNELS)
    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(frames * channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)
    return output_buf


def test_ugen_samples_mono():
    """A buffered global UGen yields its most recent samples."""
    chuck = make_chuck()
    success, _ = chuck.compile_code(TAP_CODE)
    assert success
    run_frames(chuck)

    samples = chuck.get_ugen_samples("tap", 256)

    assert samples.shape == (256,)
    assert samples.dtype == np.float32
    assert np.any(samples != 0.0)
    # a sine through a unity gain stays in range
    assert np.max(np.abs(samples)) <= 1.0


def test_ugen_samples_tracks_signal():
    """Successive reads follow the running signal rather than repeating."""
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]
    run_frames(chuck)

    first = chuck.get_ugen_samples("tap", 128).copy()
    run_frames(chuck, frames=512, cycles=1)
    second = chuck.get_ugen_samples("tap", 128)

    assert not np.array_equal(first, second)


def test_ugen_samples_are_the_actual_signal():
    """The tap returns the waveform itself, not merely non-zero data.

    441 Hz at 44100 is exactly 10.24 cycles over 1024 frames, so the sign
    changes 20 times; a unit sine has RMS 1/sqrt(2); and consecutive samples
    step by at most 2*pi*f/sr, which a garbled or wrapped ring buffer would
    violate.
    """
    chuck = make_chuck()
    code = """
    global SinOsc osc;
    1 => osc.buffered;
    441 => osc.freq;
    1.0 => osc.gain;
    osc => dac;
    10::second => now;
    """
    assert chuck.compile_code(code)[0]
    run_frames(chuck, frames=2048, cycles=1)

    samples = chuck.get_ugen_samples("osc", 1024).astype(np.float64)

    assert np.sum(np.diff(np.signbit(samples))) == 20
    assert np.sqrt(np.mean(samples**2)) == pytest.approx(1 / np.sqrt(2), abs=0.02)
    assert np.max(np.abs(samples)) == pytest.approx(1.0, abs=0.01)

    max_step = 2 * np.pi * 441 / 44100
    assert np.max(np.abs(np.diff(samples))) <= max_step * 1.01


def test_ugen_samples_multichannel_is_channel_major():
    """Multichannel results are one channel after another, not interleaved.

    Hard-panning left silences the right channel, so a channel-major read has
    all the energy in row 0 and none in row 1. An interleaved buffer would
    instead split the energy evenly across both halves.
    """
    chuck = make_chuck()
    code = """
    global Pan2 p;
    1 => p.buffered;
    SinOsc s => p => dac;
    440 => s.freq;
    1.0 => s.gain;
    -1.0 => p.pan;
    10::second => now;
    """
    assert chuck.compile_code(code)[0]
    run_frames(chuck, frames=2048, cycles=1)

    samples = chuck.get_ugen_samples("p", 256, 2).astype(np.float64)

    left_rms = np.sqrt(np.mean(samples[0] ** 2))
    right_rms = np.sqrt(np.mean(samples[1] ** 2))

    assert left_rms == pytest.approx(1 / np.sqrt(2), abs=0.05)
    assert right_rms == 0.0


def test_ugen_samples_outlive_the_instance():
    """The returned array owns its buffer, so it survives the VM."""
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]
    run_frames(chuck)

    samples = chuck.get_ugen_samples("tap", 128)
    expected = samples.tolist()

    chuck.shutdown()
    del chuck
    gc.collect()

    assert samples.tolist() == expected
    assert np.any(samples != 0.0)


def test_ugen_samples_unbuffered_reads_zero():
    """Without buffered(1) ChucK fills the buffer with zeros."""
    chuck = make_chuck()
    code = """
    global Gain tap;
    SinOsc s => tap => dac;
    10::second => now;
    """
    assert chuck.compile_code(code)[0]
    run_frames(chuck)

    samples = chuck.get_ugen_samples("tap", 128)

    assert np.all(samples == 0.0)


def test_ugen_samples_unknown_name():
    """Reading a UGen that does not exist is an error, not silence."""
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]
    run_frames(chuck)

    with pytest.raises(RuntimeError, match="nosuchugen"):
        chuck.get_ugen_samples("nosuchugen", 64)


def test_ugen_samples_channel_mismatch():
    """The multichannel read requires an exact channel count match."""
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]
    run_frames(chuck)

    with pytest.raises(RuntimeError):
        chuck.get_ugen_samples("tap", 64, 7)


def test_ugen_samples_validates_arguments():
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]

    with pytest.raises(ValueError):
        chuck.get_ugen_samples("tap", 0)
    with pytest.raises(ValueError):
        chuck.get_ugen_samples("tap", 64, 0)


def test_ugen_samples_multichannel_shape():
    """A stereo global UGen reads back channel-major."""
    chuck = make_chuck()
    code = """
    global Pan2 tap;
    1 => tap.buffered;
    SinOsc s => tap => dac;
    440 => s.freq;
    1.0 => s.gain;
    10::second => now;
    """
    assert chuck.compile_code(code)[0]
    run_frames(chuck)

    samples = chuck.get_ugen_samples("tap", 64, 2)

    assert samples.shape == (2, 64)
    assert samples.dtype == np.float32
    assert np.any(samples != 0.0)


# -----------------------------------------------------------------------------
# taps: capturing on the audio thread, which is what makes reads safe while
# real-time audio is running
# -----------------------------------------------------------------------------

SINE_CODE = """
global SinOsc osc;
1 => osc.buffered;
441 => osc.freq;
1.0 => osc.gain;
osc => dac;
1000::second => now;
"""

# a 441 Hz sine at 44100 cannot step by more than this between samples, so a
# larger jump means the read was spliced from two different points in the ring
MAX_SINE_STEP = 2 * np.pi * 441 / 44100


def test_tap_registration_lifecycle():
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]

    assert chuck.list_taps() == []
    chuck.add_tap("tap")
    assert chuck.list_taps() == ["tap"]

    # re-registering reconfigures rather than consuming a second slot
    chuck.add_tap("tap", 1, 4096)
    assert chuck.list_taps() == ["tap"]

    assert chuck.remove_tap("tap") is True
    assert chuck.remove_tap("tap") is False
    assert chuck.list_taps() == []


def test_tap_registration_validates_arguments():
    chuck = make_chuck()

    with pytest.raises(ValueError):
        chuck.add_tap("", 1, 1024)
    with pytest.raises(ValueError):
        chuck.add_tap("tap", 0, 1024)
    with pytest.raises(ValueError):
        chuck.add_tap("tap", 1, 0)


def test_tap_slots_are_finite():
    chuck = make_chuck()
    for i in range(8):
        chuck.add_tap(f"tap{i}", 1, 64)

    with pytest.raises(RuntimeError, match="No free tap slots"):
        chuck.add_tap("one_too_many", 1, 64)

    for i in range(8):
        chuck.remove_tap(f"tap{i}")


def test_taps_do_not_leak_across_instances():
    """A new instance must not inherit taps from a destroyed one.

    Tap slots are keyed by the ChucK instance pointer, and the allocator hands a
    destroyed instance's address straight to the next one. An instance collected
    by the garbage collector never runs the shutdown path, so without an
    explicit release its registrations outlived it: 18 of 20 fresh instances
    picked up the dead one's tap, and CI caught it as a stale name in
    list_taps() several tests later.
    """
    leaked = []
    for i in range(20):
        chuck = make_chuck()
        if chuck.list_taps():
            leaked.append((i, chuck.list_taps()))
        chuck.add_tap("leaky", 1, 64)  # deliberately never removed
        del chuck
        gc.collect()

    assert leaked == []


def test_offline_reads_ignore_taps():
    """With no audio thread there is nothing to race, so reads stay direct."""
    chuck = make_chuck()
    assert chuck.compile_code(TAP_CODE)[0]
    chuck.add_tap("tap")
    run_frames(chuck)

    # the tap has captured nothing (no audio callbacks), yet the read works
    samples = chuck.get_ugen_samples("tap", 256)
    assert np.any(samples != 0.0)


@pytest.mark.realtime
def test_realtime_reads_require_a_tap():
    """An unregistered read during real-time audio is refused, not raced."""
    chuck = make_chuck()
    assert chuck.compile_code(SINE_CODE)[0]

    if not numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2):
        pytest.skip("no real-time audio device")

    try:
        with pytest.raises(RuntimeError, match="add_tap"):
            chuck.get_ugen_samples("osc", 1024)

        chuck.add_tap("osc", 1, 8192)
        require_audible_tap(chuck, "osc")
        assert np.any(chuck.get_ugen_samples("osc", 1024) != 0.0)

        # and once unregistered it is refused again
        assert chuck.remove_tap("osc") is True
        with pytest.raises(RuntimeError, match="add_tap"):
            chuck.get_ugen_samples("osc", 1024)
    finally:
        numchuck.stop_audio()
        numchuck.shutdown_audio()


@pytest.mark.realtime
def test_realtime_tap_reads_are_never_torn():
    """Hammer a tap while the audio thread writes it and check every sample.

    Reading ChucK's UGen buffer directly here tears: its 8192-sample ring has
    no synchronization, so a read of the full ring gets spliced when the audio
    thread laps into the window mid-copy. Measured at 0.3% of reads, with
    discontinuities nine times the waveform's own maximum step.
    """
    chuck = make_chuck()
    assert chuck.compile_code(SINE_CODE)[0]
    chuck.add_tap("osc", 1, 8192)

    if not numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2):
        pytest.skip("no real-time audio device")

    try:
        require_audible_tap(chuck, "osc")

        reads = 0
        worst = 0.0
        loudest = 0.0
        deadline = time.time() + 1.5
        while time.time() < deadline:
            samples = chuck.get_ugen_samples("osc", 8192).astype(np.float64)
            worst = max(worst, float(np.max(np.abs(np.diff(samples)))))
            loudest = max(loudest, float(np.max(np.abs(samples))))
            reads += 1

        assert reads > 100  # a meaningful number of chances to catch a tear
        # Silence has no discontinuities either, so the tear check only means
        # something once there is a signal to tear.
        assert loudest > 0.1, f"tap carried no audible signal (peak {loudest})"
        assert worst <= MAX_SINE_STEP * 1.05
    finally:
        numchuck.stop_audio()
        numchuck.shutdown_audio()


@pytest.mark.realtime
def test_realtime_tap_channel_count_must_match():
    chuck = make_chuck()
    assert chuck.compile_code(SINE_CODE)[0]
    chuck.add_tap("osc", 1, 1024)

    if not numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2):
        pytest.skip("no real-time audio device")

    try:
        time.sleep(0.2)
        with pytest.raises(ValueError, match="registered for 1 channel"):
            chuck.get_ugen_samples("osc", 256, 2)
    finally:
        numchuck.stop_audio()
        numchuck.shutdown_audio()


@pytest.mark.realtime
def test_tap_keeps_more_history_than_one_block():
    """The tap accumulates across callbacks, so reads are not block-limited."""
    chuck = make_chuck()
    assert chuck.compile_code(SINE_CODE)[0]
    chuck.add_tap("osc", 1, 8192)

    if not numchuck.start_audio(
        chuck, sample_rate=44100, num_dac_channels=2, buffer_size=512
    ):
        pytest.skip("no real-time audio device")

    try:
        require_audible_tap(chuck, "osc")
        time.sleep(0.5)  # >> 8192 frames at 44100
        samples = chuck.get_ugen_samples("osc", 8192).astype(np.float64)

        # every frame is real audio, not zero padding, and continuous
        assert np.all(samples[:512] != 0.0)
        assert np.max(np.abs(np.diff(samples))) <= MAX_SINE_STEP * 1.05
    finally:
        numchuck.stop_audio()
        numchuck.shutdown_audio()


def test_high_level_tap_api():
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    assert chuck.compile(TAP_CODE)[0]
    chuck.run(512)

    assert chuck.taps == []
    chuck.add_tap("tap", 1, 4096)
    assert chuck.taps == ["tap"]
    assert np.any(chuck.ugen_samples("tap", 256) != 0.0)
    assert chuck.remove_tap("tap") is True
    assert chuck.taps == []
    chuck.close()


def test_high_level_ugen_samples():
    """The Chuck wrapper exposes the same tap."""
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    assert chuck.compile(TAP_CODE)[0]
    chuck.run(512)

    samples = chuck.ugen_samples("tap", 256)

    assert samples.shape == (256,)
    assert np.any(samples != 0.0)
    chuck.close()
