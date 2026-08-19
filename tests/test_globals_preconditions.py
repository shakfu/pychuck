"""The globals bindings must raise, never segfault, on a VM that is not running.

`ChucK::globals()` returns NULL until the VM is *running*, not merely
initialized. Nearly every binding used to call straight through the returned
pointer, so touching a global on a VM that had been `init()`'d but never
`start()`'d was a null dereference: SIGSEGV, no traceback, nothing the caller
could catch. `require_globals()` in `src/_numchuck.cpp` now guards every one.

These run in-process, so a regression takes the whole test session down rather
than producing a failure. That is inherent to what is being guarded -- the
point of the fix is that the process survives.
"""

from __future__ import annotations

import pytest

from numchuck import Chuck
from numchuck import _numchuck


def _noop(*args: object) -> None:
    """Callback for the async getters, which never fires in these tests."""


# (name, call) for every binding that reaches the globals manager.
GLOBALS_CALLS = [
    ("set_global_int", lambda c: c.set_global_int("x", 1)),
    ("set_global_float", lambda c: c.set_global_float("x", 1.0)),
    ("set_global_string", lambda c: c.set_global_string("x", "v")),
    ("get_global_int", lambda c: c.get_global_int("x", _noop)),
    ("get_global_float", lambda c: c.get_global_float("x", _noop)),
    ("get_global_string", lambda c: c.get_global_string("x", _noop)),
    ("set_global_int_array", lambda c: c.set_global_int_array("a", [1, 2])),
    ("set_global_float_array", lambda c: c.set_global_float_array("a", [1.0])),
    ("set_global_int_array_value", lambda c: c.set_global_int_array_value("a", 0, 1)),
    ("set_global_float_array_value", lambda c: c.set_global_float_array_value("a", 0, 1.0)),
    (
        "set_global_associative_int_array_value",
        lambda c: c.set_global_associative_int_array_value("a", "k", 1),
    ),
    (
        "set_global_associative_float_array_value",
        lambda c: c.set_global_associative_float_array_value("a", "k", 1.0),
    ),
    ("get_global_int_array", lambda c: c.get_global_int_array("a", _noop)),
    ("get_global_float_array", lambda c: c.get_global_float_array("a", _noop)),
    ("get_global_int_array_value", lambda c: c.get_global_int_array_value("a", 0, _noop)),
    (
        "get_global_float_array_value",
        lambda c: c.get_global_float_array_value("a", 0, _noop),
    ),
    (
        "get_global_associative_int_array_value",
        lambda c: c.get_global_associative_int_array_value("a", "k", _noop),
    ),
    (
        "get_global_associative_float_array_value",
        lambda c: c.get_global_associative_float_array_value("a", "k", _noop),
    ),
    ("get_ugen_samples", lambda c: c.get_ugen_samples("osc", 64, 1)),
    ("signal_global_event", lambda c: c.signal_global_event("e")),
    ("broadcast_global_event", lambda c: c.broadcast_global_event("e")),
    ("listen_for_global_event", lambda c: c.listen_for_global_event("e", _noop, True)),
    (
        "stop_listening_for_global_event",
        lambda c: c.stop_listening_for_global_event("e", 0),
    ),
    ("get_all_globals", lambda c: c.get_all_globals()),
    ("clear_vm", lambda c: c.clear_vm()),
    ("clear_globals", lambda c: c.clear_globals()),
    ("reset_shred_id", lambda c: c.reset_shred_id()),
]

CALL_IDS = [name for name, _ in GLOBALS_CALLS]


class TestNotStarted:
    """init() without start(): the manager does not exist yet."""

    @pytest.mark.parametrize("name,call", GLOBALS_CALLS, ids=CALL_IDS)
    def test_raises_instead_of_crashing(self, name, call):
        chuck = _numchuck.ChucK()
        chuck.init()
        try:
            with pytest.raises(RuntimeError, match="not running"):
                call(chuck)
        finally:
            chuck.shutdown()

    def test_message_names_the_remedy(self):
        chuck = _numchuck.ChucK()
        chuck.init()
        try:
            with pytest.raises(RuntimeError) as excinfo:
                chuck.set_global_int("x", 1)
        finally:
            chuck.shutdown()

        message = str(excinfo.value)
        assert "start()" in message
        assert "run()" in message


class TestNotInitialized:
    """No init() at all: reported separately, because the fix differs."""

    @pytest.mark.parametrize("name,call", GLOBALS_CALLS, ids=CALL_IDS)
    def test_raises_instead_of_crashing(self, name, call):
        chuck = _numchuck.ChucK()
        with pytest.raises(RuntimeError, match="not initialized"):
            call(chuck)

    def test_message_distinguishes_the_two_states(self):
        uninitialized = _numchuck.ChucK()
        with pytest.raises(RuntimeError) as no_init:
            uninitialized.set_global_int("x", 1)

        initialized = _numchuck.ChucK()
        initialized.init()
        try:
            with pytest.raises(RuntimeError) as no_start:
                initialized.set_global_int("x", 1)
        finally:
            initialized.shutdown()

        assert "init()" in str(no_init.value)
        assert str(no_init.value) != str(no_start.value)


class TestStartedStillWorks:
    """The guard must not have cost the working path anything."""

    @pytest.fixture
    def started(self):
        chuck = _numchuck.ChucK()
        chuck.init()
        chuck.start()
        yield chuck
        chuck.shutdown()

    def test_set_and_list_globals(self, started):
        started.set_global_int("counter", 7)
        assert isinstance(started.get_all_globals(), list)

    def test_events(self, started):
        started.signal_global_event("trigger")
        started.broadcast_global_event("trigger")

    def test_vm_messages(self, started):
        started.clear_globals()
        started.reset_shred_id()

    def test_arrays(self, started):
        started.set_global_int_array("arr", [1, 2, 3])
        started.set_global_float_array("farr", [1.0, 2.0])
        started.set_global_associative_int_array_value("map", "k", 5)

    def test_round_trip_through_a_running_vm(self):
        """The guard sits in front of behaviour that still has to work."""
        with Chuck(input_channels=0) as chuck:
            chuck.compile("global int x; 7 => x; while (true) { 1::samp => now; }")
            chuck.run(256)
            assert chuck.get_int("x") == 7


class TestRunStartsTheVm:
    """run() starts the VM implicitly, which is why offline code never hit this."""

    def test_globals_work_after_a_first_run(self):
        chuck = _numchuck.ChucK()
        chuck.init()
        try:
            with pytest.raises(RuntimeError):
                chuck.set_global_int("x", 1)

            import numpy as np

            # Both buffers are frames * channels; a bare ChucK defaults to two
            # channels each way, so neither may be empty.
            frames = 256
            in_channels = chuck.get_param_int(_numchuck.PARAM_INPUT_CHANNELS)
            out_channels = chuck.get_param_int(_numchuck.PARAM_OUTPUT_CHANNELS)
            chuck.run(
                np.zeros(frames * in_channels, dtype=np.float32),
                np.zeros(frames * out_channels, dtype=np.float32),
                frames,
            )

            chuck.set_global_int("x", 1)  # no longer raises
        finally:
            chuck.shutdown()
