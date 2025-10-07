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

#include <mutex>
#include <stdexcept>
#include <sstream>
#include <unordered_map>
#include <memory>

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

// Global callback storage for get/listen operations
// Maps callback ID to Python callable
static std::unordered_map<int, nb::callable> g_callbacks;
static std::mutex g_callback_mutex;
static int g_next_callback_id = 1;

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

        // Color/display methods
        .def("toggle_global_color_textoutput",
            &ChucK::toggleGlobalColorTextoutput,
            "onOff"_a,
            "Set whether ChucK generates color output for messages")

        // Chugin methods
        .def("probe_chugins",
            &ChucK::probeChugins,
            "Probe and print info on all chugins")

        // Callback methods
        .def("set_chout_callback",
            [](ChucK& self, nb::callable callback) {
                static nb::callable stored_callback;
                stored_callback = callback;
                return self.setChoutCallback([](const char* msg) {
                    nb::gil_scoped_acquire acquire;
                    stored_callback(msg);
                });
            },
            "callback"_a,
            "Set callback for chout output")
        .def("set_cherr_callback",
            [](ChucK& self, nb::callable callback) {
                static nb::callable stored_callback;
                stored_callback = callback;
                return self.setCherrCallback([](const char* msg) {
                    nb::gil_scoped_acquire acquire;
                    stored_callback(msg);
                });
            },
            "callback"_a,
            "Set callback for cherr output")

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
                std::vector<Chuck_Globals_TypeValue> globals_list;
                self.globals()->get_all_global_variables(globals_list);

                std::vector<std::pair<std::string, std::string>> result;
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
                return info;
            },
            "shred_id"_a,
            "Get information about a shred")

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

                // Create replace message
                Chuck_Msg* msg = new Chuck_Msg();
                msg->type = CK_MSG_REPLACE;
                msg->param = shred_id;
                msg->code = self.vm()->carrier()->compiler->output();
                msg->args = new std::vector<std::string>();

                // Parse args if provided
                if (!args.empty()) {
                    std::istringstream iss(args);
                    std::string token;
                    while (std::getline(iss, token, ':')) {
                        msg->args->push_back(token);
                    }
                }

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
            [](nb::callable callback) {
                static nb::callable stored_callback;
                stored_callback = callback;
                return ChucK::setStdoutCallback([](const char* msg) {
                    nb::gil_scoped_acquire acquire;
                    stored_callback(msg);
                });
            },
            "callback"_a,
            "Set global stdout callback")
        .def_static("set_stderr_callback",
            [](nb::callable callback) {
                static nb::callable stored_callback;
                stored_callback = callback;
                return ChucK::setStderrCallback([](const char* msg) {
                    nb::gil_scoped_acquire acquire;
                    stored_callback(msg);
                });
            },
            "callback"_a,
            "Set global stderr callback");

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
