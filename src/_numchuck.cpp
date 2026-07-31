// Prevent Windows min/max macros from interfering with std::min/std::max
#ifdef _WIN32
#define NOMINMAX
#endif

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/list.h>
#include <nanobind/stl/pair.h>
#include <nanobind/ndarray.h>
#include <nanobind/make_iterator.h>

#include "chuck.h"
#include "chuck_audio.h"
#include "chuck_globals.h"
#include "chuck_vm.h"
#include "util_platforms.h"  // For ck_usleep
#include "constants.h"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <sstream>
#include <unordered_map>
#include <memory>
#include <cstdint>

namespace nb = nanobind;
using namespace nb::literals;

// Mutex for audio state protection
static std::mutex g_audio_mutex;

// Thread-local storage for current ChucK instance (used by chout/cherr callbacks)
static thread_local ChucK* g_current_chuck = nullptr;

// Audio metering - atomic floats for thread-safe access from Python
static std::atomic<float> g_meter_rms_left{0.0f};
static std::atomic<float> g_meter_rms_right{0.0f};
static std::atomic<float> g_meter_peak_left{0.0f};
static std::atomic<float> g_meter_peak_right{0.0f};

// Global UGen taps.
//
// Reading a global UGen's buffer straight from Python while real-time audio
// runs is a data race: Chuck_UGen keeps an 8192-sample AccumBuffer whose write
// offset is a plain integer, and get_most_recent() memcpy's out of it with no
// synchronization at all. With a read close to the ring size the audio thread
// laps into the window mid-copy and the caller gets a spliced waveform -- 0.3%
// of 8192-frame reads in a 3-second measurement, with discontinuities 9x the
// signal's own maximum sample-to-sample step.
//
// So the sample fetch moves to the audio thread, where it runs right after
// chuck->run() returns and nothing else is writing. Each block is appended to a
// per-tap ring published under a seqlock: the audio thread never blocks, and a
// Python reader that collides with a publish retries instead of returning
// spliced data.
namespace {

constexpr size_t CK_MAX_TAPS = 8;
constexpr size_t CK_TAP_NAME_MAX = 128;
constexpr int CK_TAP_READ_ATTEMPTS = 64;
constexpr t_CKUINT CK_TAP_RETRY_USEC = 200;

struct TapSlot {
    // published state, read by both threads
    std::atomic<bool> active{false};
    std::atomic<uint64_t> seq{0};            // even: stable, odd: publish in progress
    std::atomic<size_t> write_pos{0};        // next frame index in the ring
    std::atomic<uint64_t> frames_written{0};

    // configuration, only touched while the slot is inactive
    ChucK* owner{nullptr};
    char name[CK_TAP_NAME_MAX]{};
    int channels{1};
    size_t capacity{0};                      // frames of history

    std::vector<SAMPLE> ring;                // channels * capacity, channel-major
    std::vector<SAMPLE> staging;             // channels * capacity scratch
};

TapSlot g_taps[CK_MAX_TAPS];
std::mutex g_tap_mutex;                      // serializes registration from Python
std::atomic<uint64_t> g_audio_callback_count{0};
std::atomic<ChucK*> g_audio_chuck{nullptr};  // instance currently driving audio

// Called from the audio thread once per block, after the VM has run.
void capture_taps(ChucK* chuck, t_CKUINT numFrames) {
    Chuck_Globals_Manager* globals = chuck->globals();
    if (!globals) return;

    for (TapSlot& slot : g_taps) {
        if (!slot.active.load(std::memory_order_acquire)) continue;
        if (slot.owner != chuck) continue;

        size_t frames = std::min(static_cast<size_t>(numFrames), slot.capacity);
        if (frames == 0) continue;

        // Caveat: ChucK resolves the name through a std::map<std::string, ...>
        // whose UGen pointers it keeps private, so this lookup builds a string
        // temporary on the audio thread -- heap-free only for names short
        // enough for the small-string optimization. It runs once per active tap
        // per block and taps are capped, so the cost is bounded; chuck-max does
        // the same thing in its perform routine.
        bool ok = (slot.channels == 1)
            ? globals->getGlobalUGenSamples(slot.name, slot.staging.data(),
                                            static_cast<int>(frames))
            : globals->getGlobalUGenSamplesMulti(slot.name, slot.staging.data(),
                                                 static_cast<int>(frames), slot.channels);
        if (!ok) continue;

        // publish: odd sequence marks the ring as in flux
        slot.seq.fetch_add(1, std::memory_order_acq_rel);
        std::atomic_thread_fence(std::memory_order_release);

        size_t pos = slot.write_pos.load(std::memory_order_relaxed);
        size_t first = std::min(frames, slot.capacity - pos);
        for (int c = 0; c < slot.channels; c++) {
            SAMPLE* dst = slot.ring.data() + static_cast<size_t>(c) * slot.capacity;
            const SAMPLE* src = slot.staging.data() + static_cast<size_t>(c) * frames;
            memcpy(dst + pos, src, first * sizeof(SAMPLE));
            if (frames > first) {
                memcpy(dst, src + first, (frames - first) * sizeof(SAMPLE));
            }
        }

        slot.write_pos.store((pos + frames) % slot.capacity, std::memory_order_relaxed);
        slot.frames_written.fetch_add(frames, std::memory_order_relaxed);
        slot.seq.fetch_add(1, std::memory_order_release);
    }
}

// Find the slot serving a name for an instance, or nullptr
TapSlot* find_tap(ChucK* chuck, const std::string& name, bool active_only) {
    for (TapSlot& slot : g_taps) {
        if (active_only && !slot.active.load(std::memory_order_acquire)) continue;
        if (slot.owner != chuck) continue;
        if (name == slot.name) return &slot;
    }
    return nullptr;
}

bool audio_running_for(ChucK* chuck) {
    return g_audio_chuck.load(std::memory_order_acquire) == chuck;
}

// After deactivating a slot, wait for the audio thread to leave it before its
// configuration is touched again. Bounded: a stalled or stopped audio thread
// must not hang the caller.
void wait_for_audio_quiescence(ChucK* chuck) {
    if (!audio_running_for(chuck)) return;

    nb::gil_scoped_release release;
    uint64_t start = g_audio_callback_count.load(std::memory_order_acquire);
    for (int i = 0; i < 200; i++) {
        if (g_audio_callback_count.load(std::memory_order_acquire) - start >= 2) return;
        ck_usleep(1000);
    }
}

// Copy the most recent num_frames from a tap's ring, retrying if the audio
// thread publishes during the copy. Returns false if it never settles.
bool read_tap_snapshot(TapSlot& slot, size_t num_frames, SAMPLE* out) {
    size_t channels = static_cast<size_t>(slot.channels);

    for (int attempt = 0; attempt < CK_TAP_READ_ATTEMPTS; attempt++) {
        // back off after a collision rather than spinning: a publish takes
        // microseconds, so a bare retry loop would burn every attempt inside
        // the one window it is waiting on
        if (attempt > 0) ck_usleep(CK_TAP_RETRY_USEC);

        uint64_t before = slot.seq.load(std::memory_order_acquire);
        if (before & 1) continue;  // publish in progress

        size_t pos = slot.write_pos.load(std::memory_order_relaxed);
        uint64_t available = slot.frames_written.load(std::memory_order_relaxed);

        // frames actually backed by captured audio; anything older stays zero
        size_t have = static_cast<size_t>(
            std::min<uint64_t>(std::min<uint64_t>(available, slot.capacity), num_frames));
        size_t lead = num_frames - have;
        // pos is one past the newest frame, so the window starts `have` behind it
        size_t start = (pos + slot.capacity - have) % slot.capacity;
        size_t first = std::min(have, slot.capacity - start);

        for (size_t c = 0; c < channels; c++) {
            const SAMPLE* src = slot.ring.data() + c * slot.capacity;
            SAMPLE* dst = out + c * num_frames;
            memset(dst, 0, lead * sizeof(SAMPLE));
            memcpy(dst + lead, src + start, first * sizeof(SAMPLE));
            if (have > first) {
                memcpy(dst + lead + first, src, (have - first) * sizeof(SAMPLE));
            }
        }

        std::atomic_thread_fence(std::memory_order_acquire);
        if (slot.seq.load(std::memory_order_relaxed) == before) return true;
    }
    return false;
}

}  // namespace

// Audio callback function - uses userData to get ChucK instance
static void audio_callback_func(SAMPLE* input, SAMPLE* output, t_CKUINT numFrames,
                                t_CKUINT numInChans, t_CKUINT numOutChans, void* userData) {
    ChucK* chuck = static_cast<ChucK*>(userData);
    if (chuck) {
        // Set current ChucK instance for output callbacks
        g_current_chuck = chuck;
        chuck->run(input, output, numFrames);
        // sample any registered global UGens here, while the VM is between
        // blocks and nothing is writing their buffers
        capture_taps(chuck, numFrames);
        g_current_chuck = nullptr;
        g_audio_callback_count.fetch_add(1, std::memory_order_release);

        // Calculate audio meters after processing
        if (numOutChans >= 2 && numFrames > 0) {
            float sum_sq_left = 0.0f;
            float sum_sq_right = 0.0f;
            float peak_left = 0.0f;
            float peak_right = 0.0f;

            for (t_CKUINT i = 0; i < numFrames; i++) {
                float left = static_cast<float>(output[i * numOutChans]);
                float right = static_cast<float>(output[i * numOutChans + 1]);

                sum_sq_left += left * left;
                sum_sq_right += right * right;
                peak_left = std::max(peak_left, std::abs(left));
                peak_right = std::max(peak_right, std::abs(right));
            }

            // Store RMS and peak values
            g_meter_rms_left.store(std::sqrt(sum_sq_left / numFrames), std::memory_order_relaxed);
            g_meter_rms_right.store(std::sqrt(sum_sq_right / numFrames), std::memory_order_relaxed);
            g_meter_peak_left.store(peak_left, std::memory_order_relaxed);
            g_meter_peak_right.store(peak_right, std::memory_order_relaxed);
        } else if (numOutChans == 1 && numFrames > 0) {
            // Mono output - use same value for both channels
            float sum_sq = 0.0f;
            float peak = 0.0f;

            for (t_CKUINT i = 0; i < numFrames; i++) {
                float sample = static_cast<float>(output[i]);
                sum_sq += sample * sample;
                peak = std::max(peak, std::abs(sample));
            }

            float rms = std::sqrt(sum_sq / numFrames);
            g_meter_rms_left.store(rms, std::memory_order_relaxed);
            g_meter_rms_right.store(rms, std::memory_order_relaxed);
            g_meter_peak_left.store(peak, std::memory_order_relaxed);
            g_meter_peak_right.store(peak, std::memory_order_relaxed);
        }
    }
}

// RAII wrapper for audio system lifecycle management
class AudioContext {
private:
    bool m_initialized;
    bool m_started;

public:
    AudioContext() : m_initialized(false), m_started(false) {}

    ~AudioContext() {
        cleanup();
    }

    // Delete copy/move to ensure single ownership
    AudioContext(const AudioContext&) = delete;
    AudioContext& operator=(const AudioContext&) = delete;
    AudioContext(AudioContext&&) = delete;
    AudioContext& operator=(AudioContext&&) = delete;

    bool initialize(ChucK* chuck, t_CKUINT dac_device, t_CKUINT adc_device,
                   t_CKUINT num_dac_channels, t_CKUINT num_adc_channels,
                   t_CKUINT sample_rate, t_CKUINT buffer_size, t_CKUINT num_buffers) {
        if (m_initialized) {
            cleanup();
        }

        m_initialized = ChuckAudio::initialize(
            dac_device, adc_device, num_dac_channels, num_adc_channels,
            sample_rate, buffer_size, num_buffers, audio_callback_func,
            chuck, false, nullptr
        );

        return m_initialized;
    }

    bool start() {
        if (!m_initialized) {
            return false;
        }
        m_started = ChuckAudio::start();
        if (!m_started) {
            cleanup();
        }
        return m_started;
    }

    void stop() {
        if (m_started) {
            ChuckAudio::stop();
            m_started = false;
        }
    }

    void cleanup(t_CKUINT msWait = 0) {
        if (m_started) {
            ChuckAudio::stop();
#ifdef _WIN32
            // Windows audio threads (WASAPI/DirectSound) need time to cleanly exit
            // after stop() before we can safely shutdown and release resources
            if (msWait > 0) {
                ck_usleep(msWait * 1000);  // Convert ms to us
            } else {
                ck_usleep(numchuck::WINDOWS_AUDIO_SHUTDOWN_WAIT_MS * 1000);
            }
#endif
            m_started = false;
        }
        if (m_initialized) {
            ChuckAudio::shutdown(msWait);
            m_initialized = false;
        }
    }

    bool is_initialized() const { return m_initialized; }
    bool is_started() const { return m_started; }
};

// Global audio context with mutex protection
static std::unique_ptr<AudioContext> g_audio_context;

// Global callback storage for get/listen operations
// Maps callback ID to Python callable
static std::unordered_map<int, nb::callable> g_callbacks;
static std::mutex g_callback_mutex;
static int g_next_callback_id = 1;

// Per-instance callback storage for chout/cherr
// Maps ChucK instance pointer to callback ID
static std::unordered_map<std::uintptr_t, int> g_chout_callbacks;
static std::unordered_map<std::uintptr_t, int> g_cherr_callbacks;
static std::mutex g_output_callback_mutex;

// Shred lifecycle watchers, keyed by Chuck_VM pointer. The VM hands the
// watcher the VM itself but no per-listener id, and remove_watcher() matches on
// the function pointer alone, so a single static wrapper serves every instance
// and the VM pointer is what identifies whose callback to run.
static std::unordered_map<std::uintptr_t, int> g_shred_watchers;
static std::mutex g_shred_watcher_mutex;

// Helper: Store Python callable and return ID
static int store_callback(nb::callable callback) {
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    int id = g_next_callback_id++;
    g_callbacks[id] = callback;
    return id;
}

// Helper: Remove stored callback
static void remove_callback(int id) {
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    g_callbacks.erase(id);
}

// Helper: Get stored callback
static nb::callable get_callback(int id) {
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    auto it = g_callbacks.find(id);
    if (it != g_callbacks.end()) {
        return it->second;
    }
    return nb::callable();
}

// Forward declaration: registered with the VM, so it must be a plain function
static void CK_DLL_CALL cb_shred_watcher_wrapper(Chuck_VM_Shred* shred, t_CKINT code,
                                                 t_CKINT param, Chuck_VM* vm, void* bindle);

// Helper: Clean up all callbacks for a specific ChucK instance
// Must be called before instance destruction to prevent dangling pointers
static void cleanup_instance_callbacks(ChucK* chuck) {
    std::uintptr_t key = reinterpret_cast<std::uintptr_t>(chuck);

    {
        std::lock_guard<std::mutex> lock(g_output_callback_mutex);

        // Clean up chout callback
        auto chout_it = g_chout_callbacks.find(key);
        if (chout_it != g_chout_callbacks.end()) {
            remove_callback(chout_it->second);
            g_chout_callbacks.erase(chout_it);
        }

        // Clean up cherr callback
        auto cherr_it = g_cherr_callbacks.find(key);
        if (cherr_it != g_cherr_callbacks.end()) {
            remove_callback(cherr_it->second);
            g_cherr_callbacks.erase(cherr_it);
        }
    }

    // Release this instance's taps so the audio thread cannot reach into a
    // slot pointing at a VM that is about to go away
    {
        std::lock_guard<std::mutex> lock(g_tap_mutex);
        bool released = false;
        for (TapSlot& slot : g_taps) {
            if (slot.owner == chuck && slot.active.load(std::memory_order_acquire)) {
                slot.active.store(false, std::memory_order_release);
                released = true;
            }
        }
        if (released) {
            wait_for_audio_quiescence(chuck);
        }
    }

    // Clean up the shred watcher; unsubscribing from the VM first so that no
    // notification can arrive after the Python callable is dropped
    if (chuck->vm()) {
        std::uintptr_t vm_key = reinterpret_cast<std::uintptr_t>(chuck->vm());
        std::lock_guard<std::mutex> lock(g_shred_watcher_mutex);
        auto it = g_shred_watchers.find(vm_key);
        if (it != g_shred_watchers.end()) {
            chuck->vm()->remove_watcher(cb_shred_watcher_wrapper);
            remove_callback(it->second);
            g_shred_watchers.erase(it);
        }
    }
}

// Global variable callback wrappers
static void cb_get_int_wrapper(t_CKINT callback_id, t_CKINT value) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        callback(value);
    }
    remove_callback(callback_id);
}

static void cb_get_float_wrapper(t_CKINT callback_id, t_CKFLOAT value) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        callback(value);
    }
    remove_callback(callback_id);
}

static void cb_get_string_wrapper(t_CKINT callback_id, const char* value) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        callback(std::string(value));
    }
    remove_callback(callback_id);
}

static void cb_get_int_array_wrapper(t_CKINT callback_id, t_CKINT array[], t_CKUINT size) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        std::vector<t_CKINT> vec(array, array + size);
        callback(vec);
    }
    remove_callback(callback_id);
}

static void cb_get_float_array_wrapper(t_CKINT callback_id, t_CKFLOAT array[], t_CKUINT size) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        std::vector<t_CKFLOAT> vec(array, array + size);
        callback(vec);
    }
    remove_callback(callback_id);
}

// Event listener callback wrapper (persistent callbacks)
static void cb_event_wrapper(t_CKINT callback_id) {
    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        callback();
    }
    // Note: Don't remove callback for events - they're persistent
}

// Shred lifecycle callback wrapper - looks up callback by the notifying VM.
// Called from the VM as shreds are sporked and removed, which on real-time
// audio means the audio thread; the GIL is acquired the same way the event
// listener wrapper above does it.
static void CK_DLL_CALL cb_shred_watcher_wrapper(Chuck_VM_Shred* shred, t_CKINT code,
                                                 t_CKINT param, Chuck_VM* vm, void* bindle) {
    (void)param;   // the VM always notifies with param 0
    (void)bindle;  // the VM pointer identifies the instance instead

    int callback_id = 0;
    {
        std::lock_guard<std::mutex> lock(g_shred_watcher_mutex);
        auto it = g_shred_watchers.find(reinterpret_cast<std::uintptr_t>(vm));
        if (it != g_shred_watchers.end()) {
            callback_id = it->second;
        }
    }
    if (callback_id == 0) return;

    nb::callable callback = get_callback(callback_id);
    if (callback.is_valid()) {
        nb::gil_scoped_acquire acquire;
        t_CKUINT shred_id = shred ? shred->get_id() : 0;
        std::string name = shred ? shred->name : std::string();
        callback(static_cast<t_CKINT>(code), shred_id, name);
    }
}

// Chout callback wrapper - looks up callback by current ChucK instance
static void cb_chout_wrapper(const char* msg) {
    if (!g_current_chuck) return;

    std::uintptr_t key = reinterpret_cast<std::uintptr_t>(g_current_chuck);
    int callback_id = 0;
    {
        std::lock_guard<std::mutex> lock(g_output_callback_mutex);
        auto it = g_chout_callbacks.find(key);
        if (it != g_chout_callbacks.end()) {
            callback_id = it->second;
        }
    }

    if (callback_id > 0) {
        nb::callable callback = get_callback(callback_id);
        if (callback.is_valid()) {
            nb::gil_scoped_acquire acquire;
            callback(msg);
        }
    }
}

// Cherr callback wrapper - looks up callback by current ChucK instance
static void cb_cherr_wrapper(const char* msg) {
    if (!g_current_chuck) return;

    std::uintptr_t key = reinterpret_cast<std::uintptr_t>(g_current_chuck);
    int callback_id = 0;
    {
        std::lock_guard<std::mutex> lock(g_output_callback_mutex);
        auto it = g_cherr_callbacks.find(key);
        if (it != g_cherr_callbacks.end()) {
            callback_id = it->second;
        }
    }

    if (callback_id > 0) {
        nb::callable callback = get_callback(callback_id);
        if (callback.is_valid()) {
            nb::gil_scoped_acquire acquire;
            callback(msg);
        }
    }
}

// RAII helper to set current ChucK instance for output callbacks
class ChuckContextGuard {
    ChucK* m_previous;
public:
    explicit ChuckContextGuard(ChucK* chuck) : m_previous(g_current_chuck) {
        g_current_chuck = chuck;
    }
    ~ChuckContextGuard() {
        g_current_chuck = m_previous;
    }
    ChuckContextGuard(const ChuckContextGuard&) = delete;
    ChuckContextGuard& operator=(const ChuckContextGuard&) = delete;
};

// Helper function to validate numpy array for audio processing
template<typename T>
static void validate_audio_buffer(const T& array, const char* name,
                                  size_t expected_size) {
    if (array.ndim() != 1) {
        std::ostringstream oss;
        oss << name << " must be 1-dimensional, got " << array.ndim() << " dimensions";
        throw std::invalid_argument(oss.str());
    }

    if (array.size() != expected_size) {
        std::ostringstream oss;
        oss << name << " size mismatch: expected " << expected_size
            << " elements, got " << array.size();
        throw std::invalid_argument(oss.str());
    }

    // Note: dtype and writability checked by nanobind's template parameters
    // Input arrays use ndarray<const SAMPLE, ...> (read-only)
    // Output arrays use ndarray<SAMPLE, ..., nb::c_contig> (writable, contiguous)
}

NB_MODULE(_numchuck, m) {
    m.doc() = "Python bindings for ChucK audio programming language";

    // ChucK parameter constants
    m.attr("PARAM_AUTO_DEPEND") = CHUCK_PARAM_AUTO_DEPEND;
    m.attr("PARAM_CHUGIN_ENABLE") = CHUCK_PARAM_CHUGIN_ENABLE;
    m.attr("PARAM_COMPILER_HIGHLIGHT_ON_ERROR") = CHUCK_PARAM_COMPILER_HIGHLIGHT_ON_ERROR;
    m.attr("PARAM_DEPRECATE_LEVEL") = CHUCK_PARAM_DEPRECATE_LEVEL;
    m.attr("PARAM_DUMP_INSTRUCTIONS") = CHUCK_PARAM_DUMP_INSTRUCTIONS;
    m.attr("PARAM_IMPORT_PATH_PACKAGES") = CHUCK_PARAM_IMPORT_PATH_PACKAGES;
    m.attr("PARAM_IMPORT_PATH_SYSTEM") = CHUCK_PARAM_IMPORT_PATH_SYSTEM;
    m.attr("PARAM_IMPORT_PATH_USER") = CHUCK_PARAM_IMPORT_PATH_USER;
    m.attr("PARAM_INPUT_CHANNELS") = CHUCK_PARAM_INPUT_CHANNELS;
    m.attr("PARAM_IS_REALTIME_AUDIO_HINT") = CHUCK_PARAM_IS_REALTIME_AUDIO_HINT;
    m.attr("PARAM_OTF_ENABLE") = CHUCK_PARAM_OTF_ENABLE;
    m.attr("PARAM_OTF_PORT") = CHUCK_PARAM_OTF_PORT;
    m.attr("PARAM_OTF_PRINT_WARNINGS") = CHUCK_PARAM_OTF_PRINT_WARNINGS;
    m.attr("PARAM_OUTPUT_CHANNELS") = CHUCK_PARAM_OUTPUT_CHANNELS;
    m.attr("PARAM_SAMPLE_RATE") = CHUCK_PARAM_SAMPLE_RATE;
    m.attr("PARAM_TTY_COLOR") = CHUCK_PARAM_TTY_COLOR;
    m.attr("PARAM_TTY_WIDTH_HINT") = CHUCK_PARAM_TTY_WIDTH_HINT;
    m.attr("PARAM_USER_CHUGINS") = CHUCK_PARAM_USER_CHUGINS;
    m.attr("PARAM_VERSION") = CHUCK_PARAM_VERSION;
    m.attr("PARAM_VM_ADAPTIVE") = CHUCK_PARAM_VM_ADAPTIVE;

    // Log level constants
    m.attr("LOG_NONE") = CK_LOG_NONE;
    m.attr("LOG_CORE") = CK_LOG_CORE;
    m.attr("LOG_SYSTEM") = CK_LOG_SYSTEM;
    m.attr("LOG_HERALD") = CK_LOG_HERALD;
    m.attr("LOG_WARNING") = CK_LOG_WARNING;
    m.attr("LOG_INFO") = CK_LOG_INFO;
    m.attr("LOG_DEBUG") = CK_LOG_DEBUG;
    m.attr("LOG_FINE") = CK_LOG_FINE;
    m.attr("LOG_FINER") = CK_LOG_FINER;
    m.attr("LOG_FINEST") = CK_LOG_FINEST;
    m.attr("LOG_ALL") = CK_LOG_ALL;
    m.attr("PARAM_VM_HALT") = CHUCK_PARAM_VM_HALT;
    m.attr("PARAM_WORKING_DIRECTORY") = CHUCK_PARAM_WORKING_DIRECTORY;

    // Shred watcher subscription flags (combine with |)
    m.attr("SHRED_WATCH_NONE") = static_cast<t_CKUINT>(ckvm_shreds_watch_NONE);
    m.attr("SHRED_WATCH_SPORK") = static_cast<t_CKUINT>(ckvm_shreds_watch_SPORK);
    m.attr("SHRED_WATCH_REMOVE") = static_cast<t_CKUINT>(ckvm_shreds_watch_REMOVE);
    m.attr("SHRED_WATCH_SUSPEND") = static_cast<t_CKUINT>(ckvm_shreds_watch_SUSPEND);
    m.attr("SHRED_WATCH_ACTIVATE") = static_cast<t_CKUINT>(ckvm_shreds_watch_ACTIVATE);
    m.attr("SHRED_WATCH_ALL") = static_cast<t_CKUINT>(ckvm_shreds_watch_ALL);

    // Main ChucK class
    nb::class_<ChucK>(m, "ChucK", "ChucK virtual machine and compiler")
        .def(nb::init<>(), "Create a new ChucK instance")

        // Parameter methods
        .def("set_param",
            nb::overload_cast<const std::string&, t_CKINT>(&ChucK::setParam),
            "name"_a, "value"_a,
            "Set an integer parameter")
        .def("set_param_float",
            &ChucK::setParamFloat,
            "name"_a, "value"_a,
            "Set a float parameter")
        .def("set_param_string",
            nb::overload_cast<const std::string&, const std::string&>(&ChucK::setParam),
            "name"_a, "value"_a,
            "Set a string parameter")
        .def("set_param_string_list",
            nb::overload_cast<const std::string&, const std::list<std::string>&>(&ChucK::setParam),
            "name"_a, "value"_a,
            "Set a string list parameter")
        .def("get_param_int",
            &ChucK::getParamInt,
            "name"_a,
            "Get an integer parameter")
        .def("get_param_float",
            &ChucK::getParamFloat,
            "name"_a,
            "Get a float parameter")
        .def("get_param_string",
            &ChucK::getParamString,
            "name"_a,
            "Get a string parameter")
        .def("get_param_string_list",
            &ChucK::getParamStringList,
            "name"_a,
            "Get a string list parameter")

        // Initialization methods
        .def("init",
            &ChucK::init,
            "Initialize ChucK instance with current parameters")
        .def("start",
            &ChucK::start,
            "Explicitly start ChucK (called implicitly by run if needed)")

        // Compilation methods with error handling
        .def("compile_file",
            [](ChucK& self, const std::string& path, const std::string& args,
               t_CKUINT count, bool immediate) {
                if (path.empty()) {
                    throw std::invalid_argument("File path cannot be empty");
                }
                if (count == 0) {
                    throw std::invalid_argument("Count must be at least 1");
                }
                if (!self.isInit()) {
                    throw std::runtime_error("ChucK instance not initialized. Call init() first.");
                }

                // Normalize path to use forward slashes for cross-platform compatibility
                // ChucK handles forward slashes correctly on all platforms including Windows
                std::string normalized_path = path;
                std::replace(normalized_path.begin(), normalized_path.end(), '\\', '/');

                ChuckContextGuard guard(&self);
                std::vector<t_CKUINT> shred_ids;
                t_CKBOOL result = self.compileFile(normalized_path, args, count, immediate, &shred_ids);
                return std::make_pair(result != 0, shred_ids);
            },
            "path"_a, "args"_a = "", "count"_a = 1, "immediate"_a = false,
            "Compile a ChucK file and return (success, shred_ids)")
        .def("compile_code",
            [](ChucK& self, const std::string& code, const std::string& args,
               t_CKUINT count, bool immediate, const std::string& filepath) {
                if (code.empty()) {
                    throw std::invalid_argument("Code cannot be empty");
                }
                if (count == 0) {
                    throw std::invalid_argument("Count must be at least 1");
                }
                if (!self.isInit()) {
                    throw std::runtime_error("ChucK instance not initialized. Call init() first.");
                }

                ChuckContextGuard guard(&self);
                std::vector<t_CKUINT> shred_ids;
                t_CKBOOL result = self.compileCode(code, args, count, immediate, &shred_ids, filepath);
                return std::make_pair(result != 0, shred_ids);
            },
            "code"_a, "args"_a = "", "count"_a = 1, "immediate"_a = false, "filepath"_a = "",
            "Compile ChucK code and return (success, shred_ids)")

        // Audio processing method with validation
        .def("run",
            [](ChucK& self, nb::ndarray<const SAMPLE, nb::ndim<1>, nb::device::cpu> input,
               nb::ndarray<SAMPLE, nb::ndim<1>, nb::device::cpu, nb::c_contig> output,
               t_CKINT num_frames) {
                if (!self.isInit()) {
                    throw std::runtime_error("ChucK instance not initialized. Call init() first.");
                }
                if (num_frames <= 0) {
                    throw std::invalid_argument("num_frames must be positive");
                }

                // Get channel counts from ChucK parameters
                t_CKINT num_in_channels = self.getParamInt(CHUCK_PARAM_INPUT_CHANNELS);
                t_CKINT num_out_channels = self.getParamInt(CHUCK_PARAM_OUTPUT_CHANNELS);

                // Validate buffer sizes
                size_t expected_input_size = num_frames * num_in_channels;
                size_t expected_output_size = num_frames * num_out_channels;

                validate_audio_buffer(input, "input", expected_input_size);
                validate_audio_buffer(output, "output", expected_output_size);

                ChuckContextGuard guard(&self);
                self.run(input.data(), output.data(), num_frames);
            },
            "input"_a, "output"_a, "num_frames"_a,
            "Run ChucK audio processing for num_frames")

        // Shred management
        .def("remove_all_shreds",
            &ChucK::removeAllShreds,
            "Remove all currently running shreds")

        // Status/utility methods
        .def("is_init",
            &ChucK::isInit,
            "Check if ChucK instance is initialized")
        .def("vm_running",
            &ChucK::vm_running,
            "Check if VM is running")
        .def("now",
            &ChucK::now,
            "Get current ChucK time")

        // Explicit cleanup hook run before the instance is released.
        // ChucK::shutdown() is protected as of upstream and is invoked by
        // ~ChucK(); the high-level wrapper (Chuck.close) drops its sole
        // reference right after calling this, which triggers that teardown.
        // Here we only clear the Python-side callbacks, in the correct order
        // (before VM teardown), which the destructor does not do itself.
        .def("shutdown",
            [](ChucK& self) {
                if (!self.isInit()) {
                    return;  // Already shut down or never initialized
                }

                // Clean up instance-specific callbacks before VM shutdown
                cleanup_instance_callbacks(&self);

                // Clear chout/cherr callbacks on the ChucK instance itself
                self.setChoutCallback(nullptr);
                self.setCherrCallback(nullptr);
            },
            "Clear Python-side callbacks; VM shuts down when the instance is released")

        // Color/display methods
        .def("toggle_global_color_textoutput",
            &ChucK::toggleGlobalColorTextoutput,
            "onOff"_a,
            "Set whether ChucK generates color output for messages")

        // Chugin methods
        .def("probe_chugins",
            &ChucK::probeChugins,
            "Probe and print info on all chugins")

        // Callback methods (per-instance storage)
        .def("set_chout_callback",
            [](ChucK& self, nb::callable callback) {
                std::uintptr_t key = reinterpret_cast<std::uintptr_t>(&self);
                int callback_id = store_callback(callback);
                {
                    std::lock_guard<std::mutex> lock(g_output_callback_mutex);
                    // Remove old callback if exists
                    auto it = g_chout_callbacks.find(key);
                    if (it != g_chout_callbacks.end()) {
                        remove_callback(it->second);
                    }
                    g_chout_callbacks[key] = callback_id;
                }
                return self.setChoutCallback(cb_chout_wrapper);
            },
            "callback"_a,
            "Set callback for chout output (per-instance)")
        .def("set_cherr_callback",
            [](ChucK& self, nb::callable callback) {
                std::uintptr_t key = reinterpret_cast<std::uintptr_t>(&self);
                int callback_id = store_callback(callback);
                {
                    std::lock_guard<std::mutex> lock(g_output_callback_mutex);
                    // Remove old callback if exists
                    auto it = g_cherr_callbacks.find(key);
                    if (it != g_cherr_callbacks.end()) {
                        remove_callback(it->second);
                    }
                    g_cherr_callbacks[key] = callback_id;
                }
                return self.setCherrCallback(cb_cherr_wrapper);
            },
            "callback"_a,
            "Set callback for cherr output (per-instance)")

        // Global variable management - primitives
        .def("set_global_int",
            [](ChucK& self, const std::string& name, t_CKINT value) {
                if (!self.globals()->setGlobalInt(name.c_str(), value)) {
                    throw std::runtime_error("Failed to set global int '" + name + "'");
                }
            },
            "name"_a, "value"_a,
            "Set a global int variable")
        .def("set_global_float",
            [](ChucK& self, const std::string& name, t_CKFLOAT value) {
                if (!self.globals()->setGlobalFloat(name.c_str(), value)) {
                    throw std::runtime_error("Failed to set global float '" + name + "'");
                }
            },
            "name"_a, "value"_a,
            "Set a global float variable")
        .def("set_global_string",
            [](ChucK& self, const std::string& name, const std::string& value) {
                if (!self.globals()->setGlobalString(name.c_str(), value.c_str())) {
                    throw std::runtime_error("Failed to set global string '" + name + "'");
                }
            },
            "name"_a, "value"_a,
            "Set a global string variable")
        .def("get_global_int",
            [](ChucK& self, const std::string& name, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalInt(name.c_str(), id, cb_get_int_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global int '" + name + "'");
                }
            },
            "name"_a, "callback"_a,
            "Get a global int variable (async via callback)")
        .def("get_global_float",
            [](ChucK& self, const std::string& name, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalFloat(name.c_str(), id, cb_get_float_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global float '" + name + "'");
                }
            },
            "name"_a, "callback"_a,
            "Get a global float variable (async via callback)")
        .def("get_global_string",
            [](ChucK& self, const std::string& name, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalString(name.c_str(), id, cb_get_string_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global string '" + name + "'");
                }
            },
            "name"_a, "callback"_a,
            "Get a global string variable (async via callback)")

        // Global variable management - arrays
        .def("set_global_int_array",
            [](ChucK& self, const std::string& name, const std::vector<t_CKINT>& values) {
                if (!self.globals()->setGlobalIntArray(name.c_str(),
                    const_cast<t_CKINT*>(values.data()), values.size())) {
                    throw std::runtime_error("Failed to set global int array '" + name + "'");
                }
            },
            "name"_a, "values"_a,
            "Set a global int array variable")
        .def("set_global_float_array",
            [](ChucK& self, const std::string& name, const std::vector<t_CKFLOAT>& values) {
                if (!self.globals()->setGlobalFloatArray(name.c_str(),
                    const_cast<t_CKFLOAT*>(values.data()), values.size())) {
                    throw std::runtime_error("Failed to set global float array '" + name + "'");
                }
            },
            "name"_a, "values"_a,
            "Set a global float array variable")
        .def("set_global_int_array_value",
            [](ChucK& self, const std::string& name, t_CKUINT index, t_CKINT value) {
                if (!self.globals()->setGlobalIntArrayValue(name.c_str(), index, value)) {
                    throw std::runtime_error("Failed to set global int array value '" + name + "[" + std::to_string(index) + "]'");
                }
            },
            "name"_a, "index"_a, "value"_a,
            "Set a global int array element by index")
        .def("set_global_float_array_value",
            [](ChucK& self, const std::string& name, t_CKUINT index, t_CKFLOAT value) {
                if (!self.globals()->setGlobalFloatArrayValue(name.c_str(), index, value)) {
                    throw std::runtime_error("Failed to set global float array value '" + name + "[" + std::to_string(index) + "]'");
                }
            },
            "name"_a, "index"_a, "value"_a,
            "Set a global float array element by index")
        .def("set_global_associative_int_array_value",
            [](ChucK& self, const std::string& name, const std::string& key, t_CKINT value) {
                if (!self.globals()->setGlobalAssociativeIntArrayValue(name.c_str(), key.c_str(), value)) {
                    throw std::runtime_error("Failed to set global associative int array value '" + name + "[\"" + key + "\"]'");
                }
            },
            "name"_a, "key"_a, "value"_a,
            "Set a global associative int array element by key")
        .def("set_global_associative_float_array_value",
            [](ChucK& self, const std::string& name, const std::string& key, t_CKFLOAT value) {
                if (!self.globals()->setGlobalAssociativeFloatArrayValue(name.c_str(), key.c_str(), value)) {
                    throw std::runtime_error("Failed to set global associative float array value '" + name + "[\"" + key + "\"]'");
                }
            },
            "name"_a, "key"_a, "value"_a,
            "Set a global associative float array element by key")
        .def("get_global_int_array",
            [](ChucK& self, const std::string& name, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalIntArray(name.c_str(), id, cb_get_int_array_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global int array '" + name + "'");
                }
            },
            "name"_a, "callback"_a,
            "Get a global int array (async via callback)")
        .def("get_global_float_array",
            [](ChucK& self, const std::string& name, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalFloatArray(name.c_str(), id, cb_get_float_array_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global float array '" + name + "'");
                }
            },
            "name"_a, "callback"_a,
            "Get a global float array (async via callback)")
        .def("get_global_int_array_value",
            [](ChucK& self, const std::string& name, t_CKUINT index, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalIntArrayValue(name.c_str(), id, index, cb_get_int_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global int array value '" + name + "[" + std::to_string(index) + "]'");
                }
            },
            "name"_a, "index"_a, "callback"_a,
            "Get a global int array element by index (async via callback)")
        .def("get_global_float_array_value",
            [](ChucK& self, const std::string& name, t_CKUINT index, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalFloatArrayValue(name.c_str(), id, index, cb_get_float_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global float array value '" + name + "[" + std::to_string(index) + "]'");
                }
            },
            "name"_a, "index"_a, "callback"_a,
            "Get a global float array element by index (async via callback)")
        .def("get_global_associative_int_array_value",
            [](ChucK& self, const std::string& name, const std::string& key, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalAssociativeIntArrayValue(name.c_str(), id, key.c_str(), cb_get_int_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global associative int array value '" + name + "[\"" + key + "\"]'");
                }
            },
            "name"_a, "key"_a, "callback"_a,
            "Get a global associative int array element by key (async via callback)")
        .def("get_global_associative_float_array_value",
            [](ChucK& self, const std::string& name, const std::string& key, nb::callable callback) {
                int id = store_callback(callback);
                if (!self.globals()->getGlobalAssociativeFloatArrayValue(name.c_str(), id, key.c_str(), cb_get_float_wrapper)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to get global associative float array value '" + name + "[\"" + key + "\"]'");
                }
            },
            "name"_a, "key"_a, "callback"_a,
            "Get a global associative float array element by key (async via callback)")

        // Global UGen sample access
        .def("get_ugen_samples",
            [](ChucK& self, const std::string& name, int num_frames, int num_channels) {
                if (!self.globals()) {
                    throw std::runtime_error("Globals manager not initialized");
                }
                if (num_frames <= 0) {
                    throw std::invalid_argument("num_frames must be positive");
                }
                if (num_channels <= 0) {
                    throw std::invalid_argument("num_channels must be positive");
                }

                size_t total = static_cast<size_t>(num_frames) * static_cast<size_t>(num_channels);
                SAMPLE* data = new SAMPLE[total]();

                // While the audio thread is running it is writing the UGen's
                // buffer, and reading it from here races with those writes.
                // A registered tap is captured on the audio thread instead, so
                // serve from its snapshot; without one, refuse rather than hand
                // back data that may be spliced.
                if (audio_running_for(&self)) {
                    std::lock_guard<std::mutex> lock(g_tap_mutex);
                    TapSlot* slot = find_tap(&self, name, true);
                    if (!slot) {
                        delete[] data;
                        throw std::runtime_error(
                            "Cannot read global UGen '" + name + "' while real-time audio "
                            "is running: the audio thread is writing that buffer. Register "
                            "it first with add_tap('" + name + "'), which captures the "
                            "samples on the audio thread instead");
                    }
                    if (slot->channels != num_channels) {
                        delete[] data;
                        throw std::invalid_argument(
                            "Tap '" + name + "' was registered for " +
                            std::to_string(slot->channels) + " channel(s), not " +
                            std::to_string(num_channels));
                    }
                    bool got_snapshot;
                    {
                        // the copy and any retry backoff do not touch Python
                        nb::gil_scoped_release unlocked;
                        got_snapshot = read_tap_snapshot(
                            *slot, static_cast<size_t>(num_frames), data);
                    }
                    if (!got_snapshot) {
                        delete[] data;
                        throw std::runtime_error(
                            "Timed out reading a consistent snapshot of tap '" + name + "'");
                    }

                    nb::capsule tap_owner(data, [](void* p) noexcept {
                        delete[] static_cast<SAMPLE*>(p);
                    });
                    if (num_channels == 1) {
                        size_t shape[1] = { static_cast<size_t>(num_frames) };
                        return nb::cast(nb::ndarray<nb::numpy, SAMPLE, nb::ndim<1>>(
                            data, 1, shape, tap_owner));
                    }
                    size_t shape[2] = { static_cast<size_t>(num_channels),
                                        static_cast<size_t>(num_frames) };
                    return nb::cast(nb::ndarray<nb::numpy, SAMPLE, nb::ndim<2>>(
                        data, 2, shape, tap_owner));
                }

                // Offline: the VM only advances inside run(), which holds the
                // GIL, so no other Python thread can be running it here.
                // the multichannel variant requires an exact channel match, so
                // mono goes through the single-channel call
                bool ok = (num_channels == 1)
                    ? self.globals()->getGlobalUGenSamples(name.c_str(), data, num_frames)
                    : self.globals()->getGlobalUGenSamplesMulti(name.c_str(), data, num_frames, num_channels);

                if (!ok) {
                    delete[] data;
                    throw std::runtime_error(
                        "Failed to read samples from global UGen '" + name +
                        "' (not a global UGen, or channel count mismatch)");
                }

                nb::capsule owner(data, [](void* p) noexcept {
                    delete[] static_cast<SAMPLE*>(p);
                });

                // getGlobalUGenSamplesMulti writes one channel after another,
                // so multichannel results are channel-major, not interleaved
                if (num_channels == 1) {
                    size_t shape[1] = { static_cast<size_t>(num_frames) };
                    return nb::cast(nb::ndarray<nb::numpy, SAMPLE, nb::ndim<1>>(data, 1, shape, owner));
                }
                size_t shape[2] = { static_cast<size_t>(num_channels), static_cast<size_t>(num_frames) };
                return nb::cast(nb::ndarray<nb::numpy, SAMPLE, nb::ndim<2>>(data, 2, shape, owner));
            },
            "name"_a, "num_frames"_a, "num_channels"_a = 1,
            "Read the most recent samples from a global UGen. The ChucK-side "
            "UGen must have been put in buffered mode (e.g. 'tap.buffered(1)'), "
            "otherwise the buffer reads as zeros. Returns a 1-D array for mono "
            "and a (channels, frames) array otherwise. While real-time audio is "
            "running the UGen must be registered with add_tap() first, which "
            "captures it on the audio thread; a direct read would race with it")
        .def("add_tap",
            [](ChucK& self, const std::string& name, int num_channels, int capacity_frames) {
                if (name.empty() || name.size() >= CK_TAP_NAME_MAX) {
                    throw std::invalid_argument("Tap name must be 1-127 characters");
                }
                if (num_channels <= 0) {
                    throw std::invalid_argument("num_channels must be positive");
                }
                if (capacity_frames <= 0) {
                    throw std::invalid_argument("capacity_frames must be positive");
                }

                std::lock_guard<std::mutex> lock(g_tap_mutex);

                TapSlot* slot = find_tap(&self, name, false);
                if (!slot) {
                    for (TapSlot& candidate : g_taps) {
                        if (!candidate.active.load(std::memory_order_acquire)) {
                            slot = &candidate;
                            break;
                        }
                    }
                }
                if (!slot) {
                    throw std::runtime_error(
                        "No free tap slots (maximum " + std::to_string(CK_MAX_TAPS) + ")");
                }

                // stop the audio thread using this slot before reconfiguring it
                slot->active.store(false, std::memory_order_release);
                wait_for_audio_quiescence(&self);

                slot->owner = &self;
                std::snprintf(slot->name, CK_TAP_NAME_MAX, "%s", name.c_str());
                slot->channels = num_channels;
                slot->capacity = static_cast<size_t>(capacity_frames);
                slot->ring.assign(slot->capacity * num_channels, 0.0f);
                slot->staging.assign(slot->capacity * num_channels, 0.0f);
                slot->write_pos.store(0, std::memory_order_relaxed);
                slot->frames_written.store(0, std::memory_order_relaxed);
                slot->seq.store(0, std::memory_order_relaxed);
                slot->active.store(true, std::memory_order_release);
            },
            "name"_a, "num_channels"_a = 1, "capacity_frames"_a = 8192,
            "Register a global UGen to be sampled on the audio thread, which is "
            "what makes get_ugen_samples() safe during real-time audio. Keeps "
            "capacity_frames of history; re-registering a name reconfigures it")
        .def("remove_tap",
            [](ChucK& self, const std::string& name) {
                std::lock_guard<std::mutex> lock(g_tap_mutex);
                TapSlot* slot = find_tap(&self, name, true);
                if (!slot) {
                    return false;
                }
                slot->active.store(false, std::memory_order_release);
                wait_for_audio_quiescence(&self);
                return true;
            },
            "name"_a,
            "Unregister a tap; returns False if it was not registered")
        .def("list_taps",
            [](ChucK& self) {
                std::lock_guard<std::mutex> lock(g_tap_mutex);
                std::vector<std::string> names;
                for (TapSlot& slot : g_taps) {
                    if (!slot.active.load(std::memory_order_acquire)) continue;
                    if (slot.owner != &self) continue;
                    names.push_back(slot.name);
                }
                return names;
            },
            "Names of the global UGens currently registered as taps")

        // Global event management
        .def("signal_global_event",
            [](ChucK& self, const std::string& name) {
                if (!self.globals()->signalGlobalEvent(name.c_str())) {
                    throw std::runtime_error("Failed to signal global event '" + name + "'");
                }
            },
            "name"_a,
            "Signal a global event (wakes one waiting shred)")
        .def("broadcast_global_event",
            [](ChucK& self, const std::string& name) {
                if (!self.globals()->broadcastGlobalEvent(name.c_str())) {
                    throw std::runtime_error("Failed to broadcast global event '" + name + "'");
                }
            },
            "name"_a,
            "Broadcast a global event (wakes all waiting shreds)")
        .def("listen_for_global_event",
            [](ChucK& self, const std::string& name, nb::callable callback, bool listen_forever = true) {
                int id = store_callback(callback);
                if (!self.globals()->listenForGlobalEvent(name.c_str(), id, cb_event_wrapper, listen_forever)) {
                    remove_callback(id);
                    throw std::runtime_error("Failed to listen for global event '" + name + "'");
                }
                return id;  // Return ID so user can unlisten later
            },
            "name"_a, "callback"_a, "listen_forever"_a = true,
            "Listen for a global event and call Python callback when triggered (returns listener ID)")
        .def("stop_listening_for_global_event",
            [](ChucK& self, const std::string& name, int callback_id) {
                if (!self.globals()->stopListeningForGlobalEvent(name.c_str(), callback_id, cb_event_wrapper)) {
                    throw std::runtime_error("Failed to stop listening for global event '" + name + "'");
                }
                remove_callback(callback_id);
            },
            "name"_a, "callback_id"_a,
            "Stop listening for a global event using the listener ID")

        // Introspection
        .def("get_all_globals",
            [](ChucK& self) {
                std::vector<std::pair<std::string, std::string>> result;

                // Check if globals manager is available
                if (!self.globals()) {
                    return result;  // Return empty list
                }

                std::vector<Chuck_Globals_TypeValue> globals_list;
                self.globals()->get_all_global_variables(globals_list);

                for (const auto& gv : globals_list) {
                    result.push_back({gv.type, gv.name});
                }
                return result;
            },
            "Get list of all global variables as (type, name) pairs")

        // Shred management and introspection
        .def("remove_shred",
            [](ChucK& self, t_CKUINT shred_id) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                Chuck_Msg* msg = new Chuck_Msg();
                msg->type = CK_MSG_REMOVE;
                msg->param = shred_id;
                msg->reply_cb = nullptr;
                self.vm()->queue_msg(msg, 1);
            },
            "shred_id"_a,
            "Remove a shred by ID")
        .def("get_all_shred_ids",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                std::vector<t_CKUINT> shred_ids;
                self.vm()->shreduler()->get_all_shred_ids(shred_ids);
                return shred_ids;
            },
            "Get IDs of all running shreds")
        .def("get_ready_shred_ids",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                std::vector<t_CKUINT> shred_ids;
                self.vm()->shreduler()->get_ready_shred_ids(shred_ids);
                return shred_ids;
            },
            "Get IDs of all ready (not blocked) shreds")
        .def("get_blocked_shred_ids",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                std::vector<t_CKUINT> shred_ids;
                self.vm()->shreduler()->get_blocked_shred_ids(shred_ids);
                return shred_ids;
            },
            "Get IDs of all blocked shreds")
        .def("get_last_shred_id",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                return self.vm()->last_id();
            },
            "Get ID of last sporked shred")
        .def("get_next_shred_id",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                return self.vm()->next_id();
            },
            "Get what the next shred ID will be")
        .def("get_shred_info",
            [](ChucK& self, t_CKUINT shred_id) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                Chuck_VM_Shred* shred = self.vm()->shreduler()->lookup(shred_id);
                if (!shred) {
                    throw std::runtime_error("Shred " + std::to_string(shred_id) + " not found");
                }
                // Return dict with shred info
                nb::dict info;
                info["id"] = shred->get_id();
                info["name"] = shred->name;
                info["is_running"] = shred->is_running;
                info["is_done"] = shred->is_done;
                // a shred waiting on an event holds a pointer to it
                info["is_blocked"] = (shred->event != nullptr);
                info["wake_time"] = shred->wake_time;
                info["start"] = shred->start;
                info["args"] = shred->args;
                return info;
            },
            "shred_id"_a,
            "Get information about a shred")
        .def("abort_current_shred",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                return static_cast<bool>(self.vm()->abort_current_shred());
            },
            "Abort the shred currently executing in the VM, breaking out of a "
            "shred stuck in a loop that never advances time (which remove_shred "
            "cannot reach). Only has a target while the VM is inside a compute "
            "cycle, so call it from another thread during real-time audio; "
            "returns False when there is nothing to abort")
        .def("subscribe_shred_watcher",
            [](ChucK& self, nb::callable callback, t_CKUINT options) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                std::uintptr_t vm_key = reinterpret_cast<std::uintptr_t>(self.vm());
                int id = store_callback(callback);
                {
                    std::lock_guard<std::mutex> lock(g_shred_watcher_mutex);
                    auto it = g_shred_watchers.find(vm_key);
                    if (it != g_shred_watchers.end()) {
                        remove_callback(it->second);
                    }
                    g_shred_watchers[vm_key] = id;
                }
                self.vm()->subscribe_watcher(cb_shred_watcher_wrapper, options, nullptr);
            },
            "callback"_a, "options"_a = static_cast<t_CKUINT>(ckvm_shreds_watch_ALL),
            "Call callback(code, shred_id, name) as shreds are sporked, removed, "
            "suspended or activated; code is one of the SHRED_WATCH_* flags. "
            "One watcher per instance -- subscribing again replaces it. The "
            "callback runs on whichever thread drives the VM")
        .def("remove_shred_watcher",
            [](ChucK& self) {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }
                std::uintptr_t vm_key = reinterpret_cast<std::uintptr_t>(self.vm());
                std::lock_guard<std::mutex> lock(g_shred_watcher_mutex);
                auto it = g_shred_watchers.find(vm_key);
                if (it == g_shred_watchers.end()) {
                    return false;
                }
                self.vm()->remove_watcher(cb_shred_watcher_wrapper);
                remove_callback(it->second);
                g_shred_watchers.erase(it);
                return true;
            },
            "Unsubscribe the shred watcher; returns False if none was set")

        // Adaptive block processing
        .def("set_adaptive",
            [](ChucK& self, t_CKUINT max_block_size) {
                if (!self.vm() || !self.vm()->shreduler()) {
                    throw std::runtime_error("VM not initialized");
                }

                // UGens allocate their vectorized buffers when they are
                // instantiated, sized to the shreduler's block size at that
                // moment -- and the dac, adc and bunghole are built during VM
                // init. Switching a VM that started non-adaptive into the
                // vectorized code path therefore runs it over buffers that were
                // never allocated (a segfault on the next run), and raising the
                // size past what init allocated overruns them silently.
                t_CKUINT ceiling = self.getParamInt(CHUCK_PARAM_VM_ADAPTIVE);
                if (max_block_size > 1) {
                    if (ceiling <= 1) {
                        throw std::runtime_error(
                            "VM was not initialized for adaptive block processing; "
                            "set the vm_adaptive parameter to a block size before init()");
                    }
                    if (max_block_size > ceiling) {
                        throw std::invalid_argument(
                            "max_block_size " + std::to_string(max_block_size) +
                            " exceeds the " + std::to_string(ceiling) +
                            " allocated at init; buffers are sized once");
                    }
                }

                self.vm()->shreduler()->set_adaptive(max_block_size);
            },
            "max_block_size"_a,
            "Set the shreduler's adaptive block size at runtime; a size of 1 or "
            "0 disables adaptive mode. Only valid on a VM initialized with the "
            "vm_adaptive parameter, and only up to that initial size, because "
            "the vectorized buffers are allocated once when a UGen is created")
        .def("get_adaptive",
            [](ChucK& self) {
                if (!self.vm() || !self.vm()->shreduler()) {
                    throw std::runtime_error("VM not initialized");
                }
                nb::dict info;
                info["adaptive"] = static_cast<bool>(self.vm()->shreduler()->m_adaptive);
                info["max_block_size"] = self.vm()->shreduler()->m_max_block_size;
                return info;
            },
            "Get adaptive block processing state as {adaptive, max_block_size}")

        // VM control messages
        .def("clear_vm",
            [](ChucK& self) {
                if (!self.globals()) {
                    throw std::runtime_error("Globals manager not initialized");
                }
                Chuck_Msg* msg = new Chuck_Msg();
                msg->type = CK_MSG_CLEARVM;
                msg->reply_cb = nullptr;
                if (!self.globals()->execute_chuck_msg_with_globals(msg)) {
                    throw std::runtime_error("Failed to clear VM");
                }
            },
            "Clear the VM (remove all shreds)")
        .def("clear_globals",
            [](ChucK& self) {
                if (!self.globals()) {
                    throw std::runtime_error("Globals manager not initialized");
                }
                Chuck_Msg* msg = new Chuck_Msg();
                msg->type = CK_MSG_CLEARGLOBALS;
                msg->reply_cb = nullptr;
                if (!self.globals()->execute_chuck_msg_with_globals(msg)) {
                    throw std::runtime_error("Failed to clear globals");
                }
            },
            "Clear global variables without clearing the VM")
        .def("reset_shred_id",
            [](ChucK& self) {
                if (!self.globals()) {
                    throw std::runtime_error("Globals manager not initialized");
                }
                Chuck_Msg* msg = new Chuck_Msg();
                msg->type = CK_MSG_RESET_ID;
                msg->reply_cb = nullptr;
                if (!self.globals()->execute_chuck_msg_with_globals(msg)) {
                    throw std::runtime_error("Failed to reset shred ID");
                }
            },
            "Reset the shred ID counter")
        .def("replace_shred",
            [](ChucK& self, t_CKUINT shred_id, const std::string& code, const std::string& args = "") {
                if (!self.vm()) {
                    throw std::runtime_error("VM not initialized");
                }

                // Compile code without running (count=0)
                if (!self.compileCode(code, args, 0)) {
                    throw std::runtime_error("Failed to compile replacement code");
                }

                // Use unique_ptr for exception safety during construction
                auto msg_guard = std::make_unique<Chuck_Msg>();
                auto msg_args = std::make_unique<std::vector<std::string>>();

                // Parse args if provided (may throw, but unique_ptrs handle cleanup)
                if (!args.empty()) {
                    std::istringstream iss(args);
                    std::string token;
                    while (std::getline(iss, token, ':')) {
                        msg_args->push_back(token);
                    }
                }

                // Set up message fields
                msg_guard->type = CK_MSG_REPLACE;
                msg_guard->param = shred_id;
                msg_guard->code = self.vm()->carrier()->compiler->output();
                msg_guard->args = msg_args.release();  // Transfer ownership to msg

                // process_msg takes a reference to pointer and takes ownership
                Chuck_Msg* msg = msg_guard.release();
                t_CKUINT new_id = self.vm()->process_msg(msg);
                return new_id;
            },
            "shred_id"_a, "code"_a, "args"_a = "",
            "Replace a running shred with new code (returns new shred ID)")

        // Static methods
        .def_static("version",
            &ChucK::version,
            "Get ChucK version string")
        .def_static("int_size",
            &ChucK::intSize,
            "Get ChucK int size in bits")
        .def_static("num_vms",
            &ChucK::numVMs,
            "Get number of active ChucK VMs")
        .def_static("set_log_level",
            &ChucK::setLogLevel,
            "level"_a,
            "Set ChucK log level")
        .def_static("get_log_level",
            &ChucK::getLogLevel,
            "Get ChucK log level")
        .def_static("global_cleanup",
            &ChucK::globalCleanup,
            "Global cleanup for all ChucK instances")
        .def_static("poop",
            &ChucK::poop,
            "ChucK poop compatibility")
        .def_static("set_stdout_callback",
            [](nb::handle callback) {
                static nb::object stored_callback;
                if (callback.is_none()) {
                    stored_callback = nb::object();
                    ChucK::setStdoutCallback(nullptr);
                } else {
                    stored_callback = nb::borrow(callback);
                    ChucK::setStdoutCallback([](const char* msg) {
                        nb::gil_scoped_acquire acquire;
                        if (stored_callback.is_valid() && !stored_callback.is_none()) {
                            stored_callback(msg);
                        }
                    });
                }
            },
            "callback"_a.none(),
            "Set global stdout callback (pass None to clear)")
        .def_static("set_stderr_callback",
            [](nb::handle callback) {
                static nb::object stored_callback;
                if (callback.is_none()) {
                    stored_callback = nb::object();
                    ChucK::setStderrCallback(nullptr);
                } else {
                    stored_callback = nb::borrow(callback);
                    ChucK::setStderrCallback([](const char* msg) {
                        nb::gil_scoped_acquire acquire;
                        if (stored_callback.is_valid() && !stored_callback.is_none()) {
                            stored_callback(msg);
                        }
                    });
                }
            },
            "callback"_a.none(),
            "Set global stderr callback (pass None to clear)");

    // Version function
    m.def("version", &ChucK::version, "Get ChucK version");

    // Helper function to start real-time audio with RAII management
    m.def("start_audio",
        [](ChucK& chuck, t_CKUINT sample_rate, t_CKUINT num_dac_channels,
           t_CKUINT num_adc_channels, t_CKUINT dac_device, t_CKUINT adc_device,
           t_CKUINT buffer_size, t_CKUINT num_buffers) {
            std::lock_guard<std::mutex> lock(g_audio_mutex);

            if (!chuck.isInit()) {
                throw std::runtime_error("ChucK instance not initialized. Call init() first.");
            }
            if (sample_rate == 0) {
                throw std::invalid_argument("Sample rate must be positive");
            }
            if (num_dac_channels == 0 && num_adc_channels == 0) {
                throw std::invalid_argument("At least one audio channel (DAC or ADC) required");
            }
            if (buffer_size == 0) {
                throw std::invalid_argument("Buffer size must be positive");
            }

            // Create or reset audio context
            if (!g_audio_context) {
                g_audio_context = std::make_unique<AudioContext>();
            }

            // Initialize audio with ChucK instance passed as userData
            bool success = g_audio_context->initialize(
                &chuck, dac_device, adc_device, num_dac_channels, num_adc_channels,
                sample_rate, buffer_size, num_buffers
            );

            if (!success) {
                g_audio_context.reset();
                throw std::runtime_error("Failed to initialize audio system");
            }

            success = g_audio_context->start();
            if (!success) {
                g_audio_context.reset();
                throw std::runtime_error("Failed to start audio system");
            }

            // marks the instance whose UGen buffers the audio thread is now
            // writing, which is what makes a direct tap read unsafe
            g_audio_chuck.store(&chuck, std::memory_order_release);

            return success;
        },
        "chuck"_a,
        "sample_rate"_a = numchuck::DEFAULT_SAMPLE_RATE,
        "num_dac_channels"_a = numchuck::DEFAULT_OUTPUT_CHANNELS,
        "num_adc_channels"_a = numchuck::DEFAULT_INPUT_CHANNELS,
        "dac_device"_a = numchuck::DEFAULT_DAC_DEVICE,
        "adc_device"_a = numchuck::DEFAULT_ADC_DEVICE,
        "buffer_size"_a = numchuck::DEFAULT_BUFFER_SIZE,
        "num_buffers"_a = numchuck::DEFAULT_NUM_BUFFERS,
        "Start real-time audio playback with ChucK instance");

    m.def("stop_audio",
        []() {
            std::lock_guard<std::mutex> lock(g_audio_mutex);
            if (g_audio_context) {
                g_audio_context->stop();
            }
            // no audio thread writing any more, so direct tap reads are safe again
            g_audio_chuck.store(nullptr, std::memory_order_release);
            return true;
        },
        "Stop real-time audio playback");

    m.def("shutdown_audio",
        [](t_CKUINT msWait) {
            std::lock_guard<std::mutex> lock(g_audio_mutex);
            if (g_audio_context) {
                g_audio_context->cleanup(msWait);
                g_audio_context.reset();
            }
            g_audio_chuck.store(nullptr, std::memory_order_release);
        },
        "msWait"_a = 0,
        "Shutdown audio system");

    m.def("audio_info",
        []() {
            nb::dict info;
            info["sample_rate"] = ChuckAudio::srate();
            info["num_channels_out"] = ChuckAudio::num_channels_out();
            info["num_channels_in"] = ChuckAudio::num_channels_in();
            info["buffer_size"] = ChuckAudio::buffer_size();
            return info;
        },
        "Get current audio system info");

    m.def("is_audio_running",
        []() {
            std::lock_guard<std::mutex> lock(g_audio_mutex);
            return g_audio_context && g_audio_context->is_started();
        },
        "Check if real-time audio is currently running");

    m.def("get_audio_meters",
        []() {
            nb::dict meters;
            meters["rms_left"] = g_meter_rms_left.load(std::memory_order_relaxed);
            meters["rms_right"] = g_meter_rms_right.load(std::memory_order_relaxed);
            meters["peak_left"] = g_meter_peak_left.load(std::memory_order_relaxed);
            meters["peak_right"] = g_meter_peak_right.load(std::memory_order_relaxed);
            return meters;
        },
        "Get current audio meter values (RMS and peak for left/right channels)");

    // Cleanup function to be called during module teardown
    m.def("_cleanup_callbacks",
        []() {
            {
                std::lock_guard<std::mutex> lock(g_callback_mutex);
                g_callbacks.clear();
            }
            {
                std::lock_guard<std::mutex> lock(g_output_callback_mutex);
                g_chout_callbacks.clear();
                g_cherr_callbacks.clear();
            }
            {
                std::lock_guard<std::mutex> lock(g_shred_watcher_mutex);
                g_shred_watchers.clear();
            }
            {
                std::lock_guard<std::mutex> lock(g_tap_mutex);
                for (TapSlot& slot : g_taps) {
                    slot.active.store(false, std::memory_order_release);
                }
            }
        },
        "Internal cleanup function for callbacks (called during module unload)");

    // Register cleanup to be called at module unload
    // This prevents segfault when Python objects are destroyed after Python shutdown
    nb::module_::import_("atexit").attr("register")(m.attr("_cleanup_callbacks"));
}
