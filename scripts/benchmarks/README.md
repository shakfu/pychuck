# numchuck Performance Benchmarks

This directory contains performance benchmarks for the numchuck library.

## Overview

The benchmarks measure performance across core aspects of numchuck:

1. **Code Compilation** - Speed of compiling ChucK code
2. **Audio Rendering** - Throughput of audio buffer processing
3. **Global Variables** - Latency of setting global variables
4. **Event System** - Performance of event signaling

## Running Benchmarks

### Quick Start

```bash
python benchmarks/benchmark_simple.py
```

### With uv

```bash
uv run python benchmarks/benchmark_simple.py
```

### Sample Output

```text
============================================================
numchuck Simple Performance Benchmarks
============================================================

1. Code Compilation
------------------------------------------------------------
Simple code compilation:
  Iterations:  100
  Total time:  0.0016s
  Avg time:    0.0157ms
  Ops/sec:     63833.16

2. Audio Rendering
------------------------------------------------------------
Audio rendering (512 frames):
  Iterations:  200
  Total time:  0.0133s
  Avg time:    0.0667ms
  Ops/sec:     14990.12
  Throughput:  61.29 MB/s

3. Global Variable Access
------------------------------------------------------------
Set global int:
  Iterations:  500
  Total time:  0.0001s
  Avg time:    0.0001ms
  Ops/sec:     7853363.69

4. Event Signaling
------------------------------------------------------------
Signal event:
  Iterations:  500
  Total time:  0.0001s
  Avg time:    0.0001ms
  Ops/sec:     9266292.89
```

## Benchmark Categories

### 1. Code Compilation

Measures how quickly ChucK code can be parsed and compiled:

- **Simple code**: Basic oscillator connection
- **Complex code**: Multiple UGens with control flow

**What affects performance:**

- Code complexity (number of statements, control flow)
- Number of UGens and connections
- Parser overhead

### 2. Audio Rendering

Measures audio buffer processing throughput:

- Tests multiple buffer sizes (128, 256, 512, 1024, 2048 frames)
- Reports operations per second and MB/s throughput
- Simulates real-time audio workload

**What affects performance:**

- Buffer size (larger = more efficient but higher latency)
- Number of active UGens
- Complexity of signal processing chain
- CPU cache effects

### 3. Shred Management

Measures overhead of shred lifecycle operations:

- **Spork and remove**: Create and destroy shreds
- **Replace**: Hot-swap running shred with new code
- **Remove all**: Bulk removal of multiple shreds

**What affects performance:**

- VM synchronization overhead
- Shred scheduler complexity
- Number of active shreds

### 4. Global Variables

Measures Python-ChucK communication latency:

- Set operations: int, float, string, arrays
- Get operations: Async callback invocation
- Array access by index

**What affects performance:**

- Type conversion overhead
- Callback dispatch latency
- Array size (for array operations)

### 5. Event System

Measures event-based communication:

- **Signal**: Wake single waiting listener
- **Broadcast**: Wake all waiting listeners
- **Listener registration**: Add/remove listener overhead

**What affects performance:**

- Number of registered listeners
- Callback dispatch overhead
- Thread synchronization

### 6. VM Operations

Measures VM-level operations:

- **Initialization**: ChucK instance creation and setup
- **Clear VM**: Remove all shreds and reset state

**What affects performance:**

- Resource allocation/deallocation
- Cleanup overhead

## Interpreting Results

### Metrics Explained

- **Iterations**: Number of times the operation was performed
- **Total time**: Total wall-clock time for all iterations
- **Avg time**: Average time per operation (in milliseconds)
- **Ops/sec**: Operations per second (higher is better)
- **Throughput**: For audio rendering, MB/s of audio data processed

### Performance Targets

Typical performance on modern hardware (M1 MacBook Pro as reference):

| Operation | Target | Notes |
|-----------|--------|-------|
| Simple compilation | > 500 ops/sec | Should be fast enough for livecoding |
| Audio rendering (512 frames) | > 2000 ops/sec | Real-time requires ~86 ops/sec @ 44.1kHz |
| Shred spork/remove | > 300 ops/sec | Livecoding responsiveness |
| Global var set | > 5000 ops/sec | Low overhead communication |
| Event signal | > 5000 ops/sec | Low latency triggering |

### Real-Time Audio Requirements

For real-time audio at 44100 Hz with 512-frame buffers:

- Required throughput: ~86 buffer renders/second
- This benchmark should show **20-40x** headroom for safety
- If ops/sec < 1000, real-time performance may be at risk

## Benchmark Development

### Adding New Benchmarks

1. Define a new benchmark function:

```python
def benchmark_new_feature():
    """Benchmark description."""
    chuck = numchuck.ChucK()
    chuck.init(44100, 2)

    # Setup code
    # ...

    def operation():
        # Code to benchmark
        pass

    result = benchmark(operation, iterations=100, name="Feature name")
    return [result]
```

2. Add to `run_all_benchmarks()`:

```python
print("Running new feature benchmarks...")
all_results.extend(benchmark_new_feature())
print()
```

### Best Practices

1. **Isolate operations**: Each benchmark should test one specific operation
2. **Warm up**: Consider running operation once before timing
3. **Appropriate iterations**: Choose iterations to get ~100-500ms total time
4. **Clean up**: Remove shreds and reset state between benchmarks
5. **Consistent setup**: Use same sample rate, channels across benchmarks

### Profiling

For detailed profiling, use Python's profiling tools:

```bash
# Profile the benchmark script
python -m cProfile -o benchmark.prof benchmarks/benchmark_audio.py

# View results
python -m pstats benchmark.prof
>>> sort cumtime
>>> stats 20
```

## Continuous Performance Monitoring

To track performance over time:

1. Run benchmarks on each commit:

   ```bash
   git log --oneline -1 > benchmark_results.txt
   python benchmarks/benchmark_audio.py >> benchmark_results.txt
   ```

2. Compare before/after changes:

   ```bash
   # Before changes
   python benchmarks/benchmark_audio.py > before.txt

   # Make changes...

   # After changes
   python benchmarks/benchmark_audio.py > after.txt

   # Compare
   diff before.txt after.txt
   ```

3. Watch for regressions:
   - Compilation should not get slower over time
   - Audio rendering should maintain throughput
   - Memory usage should remain stable

## Platform Differences

Performance varies by platform:

- **macOS**: CoreAudio backend, generally good performance
- **Linux**: ALSA/PulseAudio backend, performance varies by system
- **Windows**: DirectSound backend, may have higher latency

Run benchmarks on your target platform to establish baselines.

## Troubleshooting

**Benchmarks run too fast (< 10ms total time)**:

- Increase number of iterations
- More iterations = more accurate timing

**Inconsistent results**:

- Close other applications
- Run multiple times and average
- Check CPU throttling / power settings

**Lower than expected performance**:

- Check CPU usage (should not be 100%)
- Verify no other audio applications running
- Try different buffer sizes
- Profile to find bottlenecks

## Contributing

When contributing performance improvements:

1. Run benchmarks before changes (baseline)
2. Make changes
3. Run benchmarks after changes
4. Document performance delta in PR description
5. Include benchmark output in PR if significant change (> 10%)

## License

Same as numchuck project.
