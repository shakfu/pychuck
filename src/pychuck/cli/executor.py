"""
ChucK file executor for command-line execution.

Provides non-interactive execution of ChucK files with options for:
- Audio output or silent mode
- Custom sample rate and channel count
- Timed execution
"""
import sys
import time
import signal
from pathlib import Path
from typing import List, Optional


class ExecutionError(Exception):
    """Raised when ChucK file execution fails."""
    pass


def execute_files(
    files: List[str],
    srate: int = 44100,
    channels: int = 2,
    silent: bool = False,
    duration: Optional[float] = None
):
    """
    Execute ChucK files from command line.

    Args:
        files: List of ChucK file paths to execute
        srate: Sample rate (default: 44100)
        channels: Number of audio channels (default: 2)
        silent: If True, run without audio output
        duration: If specified, run for this many seconds then exit

    Raises:
        ExecutionError: If compilation or execution fails
    """
    from .. import ChucK

    # Validate files exist
    missing_files = []
    for filepath in files:
        if not Path(filepath).exists():
            missing_files.append(filepath)

    if missing_files:
        print(f"Error: Files not found:", file=sys.stderr)
        for f in missing_files:
            print(f"  {f}", file=sys.stderr)
        raise ExecutionError("One or more files not found")

    # Initialize ChucK VM
    try:
        chuck = ChucK.create(srate, channels)
    except Exception as e:
        print(f"Error: Failed to create ChucK VM: {e}", file=sys.stderr)
        raise ExecutionError(f"ChucK initialization failed: {e}")

    # Start audio if not silent
    audio_started = False
    if not silent:
        try:
            from .. import start_audio
            start_audio(chuck)
            audio_started = True
        except Exception as e:
            print(f"Warning: Failed to start audio: {e}", file=sys.stderr)
            print("Continuing in silent mode...", file=sys.stderr)

    # Setup signal handler for graceful shutdown
    shutdown_requested = [False]  # Use list to allow modification in nested function

    def signal_handler(sig, frame):
        print("\nShutdown requested...", file=sys.stderr)
        shutdown_requested[0] = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Compile and run files
    shred_ids = []
    for filepath in files:
        try:
            # Read file content
            with open(filepath, 'r') as f:
                code = f.read()

            # Compile and run
            shred_id = chuck.compile_code(code)
            if shred_id == 0:
                raise ExecutionError(f"Failed to compile {filepath}")

            shred_ids.append(shred_id)
            print(f"[shred {shred_id}] {filepath}")

        except Exception as e:
            print(f"Error compiling {filepath}: {e}", file=sys.stderr)
            # Cleanup
            if audio_started:
                from .. import stop_audio
                stop_audio()
            raise ExecutionError(f"Compilation failed: {e}")

    # Run for specified duration or until interrupted
    try:
        start_time = time.time()

        if duration is not None:
            # Run for specified duration
            print(f"Running for {duration} seconds...")
            while time.time() - start_time < duration:
                if shutdown_requested[0]:
                    break
                time.sleep(0.1)
        else:
            # Run indefinitely
            print("Running... (Ctrl-C to stop)")
            while not shutdown_requested[0]:
                time.sleep(0.1)

    finally:
        # Cleanup
        print("Cleaning up...")

        # Remove all shreds
        for shred_id in shred_ids:
            try:
                chuck.remove_shred(shred_id)
            except:
                pass

        # Stop audio
        if audio_started:
            try:
                from .. import stop_audio, shutdown_audio
                stop_audio()
                shutdown_audio()
            except:
                pass

        print("Done.")


if __name__ == '__main__':
    # For testing
    import sys
    if len(sys.argv) > 1:
        execute_files(sys.argv[1:])
    else:
        print("Usage: python -m pychuck.cli.executor <file.ck> [file2.ck ...]")
