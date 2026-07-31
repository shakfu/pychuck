"""
Tests for VM-level control and introspection: the shred lifecycle watcher,
aborting a running shred, adaptive block processing, and shred metadata.
"""

import time

import numpy as np
import pytest

from numchuck import Chuck, SHRED_WATCH_REMOVE, SHRED_WATCH_SPORK
from numchuck import _numchuck as numchuck


def make_chuck():
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    chuck.start()
    return chuck


def run_audio_cycles(chuck, cycles=3, frames=512):
    channels = chuck.get_param_int(numchuck.PARAM_OUTPUT_CHANNELS)
    input_buf = np.zeros(0, dtype=np.float32)
    output_buf = np.zeros(frames * channels, dtype=np.float32)
    for _ in range(cycles):
        chuck.run(input_buf, output_buf, frames)


# -----------------------------------------------------------------------------
# shred lifecycle watcher
# -----------------------------------------------------------------------------


def test_watcher_reports_spork_and_remove():
    chuck = make_chuck()
    events = []
    chuck.subscribe_shred_watcher(
        lambda code, sid, name: events.append((code, sid, name))
    )

    success, shred_ids = chuck.compile_code("while (true) { 10::ms => now; }")
    assert success
    run_audio_cycles(chuck)

    assert (SHRED_WATCH_SPORK, shred_ids[0]) == (events[0][0], events[0][1])
    assert events[0][2]  # shreds carry a name

    chuck.remove_shred(shred_ids[0])
    run_audio_cycles(chuck)

    codes = [code for code, _, _ in events]
    assert SHRED_WATCH_REMOVE in codes


def test_watcher_option_filters_events():
    """Subscribing to spork only must not report removals."""
    chuck = make_chuck()
    events = []
    chuck.subscribe_shred_watcher(
        lambda code, sid, name: events.append(code), SHRED_WATCH_SPORK
    )

    success, shred_ids = chuck.compile_code("while (true) { 10::ms => now; }")
    assert success
    run_audio_cycles(chuck)
    chuck.remove_shred(shred_ids[0])
    run_audio_cycles(chuck)

    assert events == [SHRED_WATCH_SPORK]


def test_watcher_replaced_and_removed():
    chuck = make_chuck()
    first, second = [], []

    chuck.subscribe_shred_watcher(lambda code, sid, name: first.append(code))
    chuck.subscribe_shred_watcher(lambda code, sid, name: second.append(code))

    assert chuck.compile_code("1::samp => now;")[0]
    run_audio_cycles(chuck)

    # only the most recent watcher is live
    assert first == []
    assert second

    assert chuck.remove_shred_watcher() is True
    assert chuck.remove_shred_watcher() is False

    before = len(second)
    assert chuck.compile_code("1::samp => now;")[0]
    run_audio_cycles(chuck)
    assert len(second) == before


def test_watcher_survives_shutdown():
    """Shutdown unsubscribes the watcher rather than leaving it dangling."""
    chuck = make_chuck()
    chuck.subscribe_shred_watcher(lambda code, sid, name: None)
    assert chuck.compile_code("1::samp => now;")[0]
    run_audio_cycles(chuck)
    chuck.shutdown()


def test_high_level_on_shred():
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    seen = []
    chuck.on_shred(lambda code, sid, name: seen.append((code, sid)))

    success, shred_ids = chuck.compile("while (true) { 10::ms => now; }")
    assert success
    chuck.run(512)

    assert seen[0] == (SHRED_WATCH_SPORK, shred_ids[0])
    assert chuck.remove_shred_watcher() is True
    chuck.close()


# -----------------------------------------------------------------------------
# abort
# -----------------------------------------------------------------------------


def test_abort_without_running_shred():
    """With no shred inside a compute cycle there is nothing to abort."""
    chuck = make_chuck()
    assert chuck.compile_code("while (true) { 10::ms => now; }")[0]
    run_audio_cycles(chuck)

    assert chuck.abort_current_shred() is False


@pytest.mark.realtime
def test_abort_breaks_out_of_runaway_shred():
    """A shred that never advances time can only be stopped by abort.

    This needs real-time audio for two reasons: the VM only has a current shred
    while it is inside a compute cycle, and an offline run() would hold the GIL
    for its whole duration, leaving no thread able to issue the abort. On the
    audio thread the runaway shred occupies compute continuously, which is
    exactly when abort has a target.
    """
    chuck = make_chuck()
    success, shred_ids = chuck.compile_code("while (true) { 1 => int x; }")
    assert success

    if not numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2):
        pytest.skip("no real-time audio device")

    try:
        time.sleep(0.5)  # let the audio thread enter the runaway shred
        assert chuck.abort_current_shred() is True

        time.sleep(0.5)
        assert shred_ids[0] not in chuck.get_all_shred_ids()
    finally:
        numchuck.stop_audio()
        numchuck.shutdown_audio()


def test_high_level_abort_shred():
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    assert chuck.compile("while (true) { 10::ms => now; }")[0]
    chuck.run(512)

    assert chuck.abort_shred() is False
    chuck.close()


# -----------------------------------------------------------------------------
# adaptive block processing
# -----------------------------------------------------------------------------


def make_adaptive_chuck(block_size=128):
    chuck = numchuck.ChucK()
    chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 0)
    chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
    chuck.set_param(numchuck.PARAM_VM_ADAPTIVE, block_size)
    chuck.init()
    chuck.start()
    return chuck


def test_adaptive_defaults_off():
    chuck = make_chuck()
    state = chuck.get_adaptive()

    assert state["adaptive"] is False
    assert state["max_block_size"] == 0


def test_adaptive_reports_init_size():
    chuck = make_adaptive_chuck(128)
    assert chuck.get_adaptive() == {"adaptive": True, "max_block_size": 128}


def test_adaptive_set_and_clear():
    chuck = make_adaptive_chuck(128)

    chuck.set_adaptive(64)
    state = chuck.get_adaptive()
    assert state["adaptive"] is True
    assert state["max_block_size"] == 64

    chuck.set_adaptive(1)
    assert chuck.get_adaptive()["adaptive"] is False


def test_adaptive_rejects_non_adaptive_vm():
    """Switching a non-adaptive VM into the vectorized path would segfault.

    The UGens the VM builds at init have no vectorized buffers in that case,
    so the binding refuses instead of crashing.
    """
    chuck = make_chuck()

    with pytest.raises(RuntimeError, match="not initialized for adaptive"):
        chuck.set_adaptive(128)

    # turning it off is always allowed, since it changes no buffer requirement
    chuck.set_adaptive(0)
    assert chuck.get_adaptive()["adaptive"] is False


def test_adaptive_rejects_growing_past_init_size():
    """Buffers are sized once; a larger block would overrun them."""
    chuck = make_adaptive_chuck(128)

    with pytest.raises(ValueError, match="exceeds"):
        chuck.set_adaptive(256)

    assert chuck.get_adaptive()["max_block_size"] == 128


def test_adaptive_does_not_disturb_audio():
    """Changing the block size mid-stream still produces audio."""
    chuck = make_adaptive_chuck(128)
    assert chuck.compile_code("SinOsc s => dac; 10::second => now;")[0]
    run_audio_cycles(chuck)

    chuck.set_adaptive(64)
    output_buf = np.zeros(512 * 2, dtype=np.float32)
    chuck.run(np.zeros(0, dtype=np.float32), output_buf, 512)

    assert np.any(output_buf != 0.0)


def test_high_level_adaptive():
    chuck = Chuck(
        sample_rate=44100, input_channels=0, output_channels=2, vm_adaptive=64
    )

    assert chuck.vm_adaptive is True
    assert chuck.adaptive == {"adaptive": True, "max_block_size": 64}

    chuck.set_adaptive(32)
    assert chuck.adaptive == {"adaptive": True, "max_block_size": 32}
    chuck.close()


def test_high_level_adaptive_flag_selects_default_size():
    """vm_adaptive=True must actually enable it, not pass a no-op size of 1."""
    chuck = Chuck(
        sample_rate=44100, input_channels=0, output_channels=2, vm_adaptive=True
    )

    assert chuck.vm_adaptive is True
    assert chuck.adaptive["adaptive"] is True
    assert chuck.adaptive["max_block_size"] > 1
    chuck.close()


def test_high_level_adaptive_off_by_default():
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)

    assert chuck.vm_adaptive is False
    assert chuck.adaptive["adaptive"] is False
    with pytest.raises(RuntimeError):
        chuck.set_adaptive(64)
    chuck.close()


# -----------------------------------------------------------------------------
# shred metadata
# -----------------------------------------------------------------------------


def test_shred_info_reports_blocked_state():
    chuck = make_chuck()
    success, shred_ids = chuck.compile_code(
        """
        global Event go;
        go => now;
        """
    )
    assert success
    run_audio_cycles(chuck)

    info = chuck.get_shred_info(shred_ids[0])
    assert info["is_blocked"] is True

    chuck.broadcast_global_event("go")
    run_audio_cycles(chuck)

    assert shred_ids[0] not in chuck.get_all_shred_ids()


def test_shred_info_reports_timing_and_args():
    chuck = make_chuck()
    success, shred_ids = chuck.compile_code(
        "while (true) { 100::ms => now; }", "alpha:beta"
    )
    assert success
    run_audio_cycles(chuck)

    info = chuck.get_shred_info(shred_ids[0])

    assert info["args"] == ["alpha", "beta"]
    assert info["is_blocked"] is False
    assert info["wake_time"] > 0.0
    assert info["start"] >= 0.0


def test_shred_info_high_level():
    chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
    success, shred_ids = chuck.compile("while (true) { 100::ms => now; }")
    assert success
    chuck.run(512)

    info = chuck.shred_info(shred_ids[0])
    assert set(info) >= {
        "id",
        "name",
        "is_running",
        "is_done",
        "is_blocked",
        "wake_time",
        "start",
        "args",
    }
    chuck.close()


def test_shred_info_missing_shred():
    chuck = make_chuck()
    with pytest.raises(RuntimeError, match="not found"):
        chuck.get_shred_info(9999)
