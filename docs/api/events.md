# Events

ChucK global events carry signals in both directions: Python can wake shreds
that are waiting on an event, and Python callbacks can fire when ChucK signals
one.

The methods themselves are documented on the [Chuck](chuck.md) page; this page
covers how they fit together.

Declare the event in ChucK first — Python can only reach a global that exists:

```python
chuck.compile("""
    global Event trigger;
    while (true) {
        trigger => now;          // block until signalled
        <<< "woke up" >>>;
    }
""")
```

## Python to ChucK

```python
chuck.signal_event("trigger")      # wake one waiting shred
chuck.broadcast_event("trigger")   # wake all of them
```

The distinction matters when several shreds wait on the same event:
[`signal_event`][numchuck.Chuck.signal_event] releases exactly one,
[`broadcast_event`][numchuck.Chuck.broadcast_event] releases every one.

Signalling an event nobody declared is not an error and does nothing.

## ChucK to Python

```python
def on_trigger():
    print("fired")

callback_id = chuck.on_event("trigger", on_trigger)
...
chuck.stop_listening_for_event("trigger", callback_id)
```

Several callbacks can listen to one event. Each registration returns its own id,
and [`stop_listening_for_event`][numchuck.Chuck.stop_listening_for_event] takes
that id — so keep it if you intend to unsubscribe.

!!! note "Callbacks run on whichever thread drives the VM"
    During real-time audio that is the audio thread, so a slow callback delays
    audio. Keep them short: queue the work rather than doing it inline.

!!! note "The VM has to advance for a callback to fire"
    Offline, nothing runs until you call `run()`. A signal followed immediately
    by an assertion will fail; render some frames in between.

Relevant methods: [`on_event`][numchuck.Chuck.on_event],
[`stop_listening_for_event`][numchuck.Chuck.stop_listening_for_event].

## Shred lifecycle

Distinct from ChucK events: a watcher reports shreds being sporked, removed,
suspended or activated, so you do not have to poll `chuck.shreds`.

```python
import numchuck

def on_change(event, shred_id, name):
    print(event, shred_id, name)

chuck.on_shred(on_change, options=numchuck.SHRED_WATCH_ALL)
```

Subscription flags are listed under [Constants](constants.md#shred-watcher-flags).
There is one watcher per instance, and it is unsubscribed on shutdown so no
notification can arrive after the Python callable is dropped. Remove it earlier
with [`remove_shred_watcher`][numchuck.Chuck.remove_shred_watcher].

See [`on_shred`][numchuck.Chuck.on_shred].
