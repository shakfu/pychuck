#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/list.h>
#include <nanobind/stl/pair.h>
#include <nanobind/ndarray.h>

#include "chuck.h"
#include "chuck_audio.h"

#include <mutex>
#include <stdexcept>
#include <sstream>

namespace nb = nanobind;
using namespace nb::literals;

// Mutex for audio state protection
static std::mutex g_audio_mutex;

// Audio callback function - uses userData to get ChucK instance
static void audio_callback_func(SAMPLE* input, SAMPLE* output, t_CKUINT numFrames,
                                t_CKUINT numInChans, t_CKUINT numOutChans, void* userData) {
    ChucK* chuck = static_cast<ChucK*>(userData);
    if (chuck) {
        chuck->run(input, output, numFrames);
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

NB_MODULE(_pychuck, m) {
    m.doc() = "Python bindings for ChucK audio programming language";

    // ChucK parameter constants
    m.attr("PARAM_VERSION") = CHUCK_PARAM_VERSION;
    m.attr("PARAM_SAMPLE_RATE") = CHUCK_PARAM_SAMPLE_RATE;
    m.attr("PARAM_INPUT_CHANNELS") = CHUCK_PARAM_INPUT_CHANNELS;
    m.attr("PARAM_OUTPUT_CHANNELS") = CHUCK_PARAM_OUTPUT_CHANNELS;
    m.attr("PARAM_VM_ADAPTIVE") = CHUCK_PARAM_VM_ADAPTIVE;
    m.attr("PARAM_VM_HALT") = CHUCK_PARAM_VM_HALT;
    m.attr("PARAM_OTF_ENABLE") = CHUCK_PARAM_OTF_ENABLE;
    m.attr("PARAM_OTF_PORT") = CHUCK_PARAM_OTF_PORT;
    m.attr("PARAM_DUMP_INSTRUCTIONS") = CHUCK_PARAM_DUMP_INSTRUCTIONS;
    m.attr("PARAM_AUTO_DEPEND") = CHUCK_PARAM_AUTO_DEPEND;
    m.attr("PARAM_DEPRECATE_LEVEL") = CHUCK_PARAM_DEPRECATE_LEVEL;
    m.attr("PARAM_WORKING_DIRECTORY") = CHUCK_PARAM_WORKING_DIRECTORY;
    m.attr("PARAM_CHUGIN_ENABLE") = CHUCK_PARAM_CHUGIN_ENABLE;
    m.attr("PARAM_USER_CHUGINS") = CHUCK_PARAM_USER_CHUGINS;

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

                std::vector<t_CKUINT> shred_ids;
                t_CKBOOL result = self.compileFile(path, args, count, immediate, &shred_ids);
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
            "Global cleanup for all ChucK instances");

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

            return success;
        },
        "chuck"_a, "sample_rate"_a = 44100, "num_dac_channels"_a = 2,
        "num_adc_channels"_a = 0, "dac_device"_a = 0, "adc_device"_a = 0,
        "buffer_size"_a = 512, "num_buffers"_a = 8,
        "Start real-time audio playback with ChucK instance");

    m.def("stop_audio",
        []() {
            std::lock_guard<std::mutex> lock(g_audio_mutex);
            if (g_audio_context) {
                g_audio_context->stop();
            }
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
}
