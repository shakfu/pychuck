#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/list.h>
#include <nanobind/stl/pair.h>
#include <nanobind/ndarray.h>

#include "chuck.h"

namespace nb = nanobind;
using namespace nb::literals;

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

        // Compilation methods
        .def("compile_file",
            [](ChucK& self, const std::string& path, const std::string& args,
               t_CKUINT count, bool immediate) {
                std::vector<t_CKUINT> shred_ids;
                t_CKBOOL result = self.compileFile(path, args, count, immediate, &shred_ids);
                return std::make_pair(result != 0, shred_ids);
            },
            "path"_a, "args"_a = "", "count"_a = 1, "immediate"_a = false,
            "Compile a ChucK file and return (success, shred_ids)")
        .def("compile_code",
            [](ChucK& self, const std::string& code, const std::string& args,
               t_CKUINT count, bool immediate, const std::string& filepath) {
                std::vector<t_CKUINT> shred_ids;
                t_CKBOOL result = self.compileCode(code, args, count, immediate, &shred_ids, filepath);
                return std::make_pair(result != 0, shred_ids);
            },
            "code"_a, "args"_a = "", "count"_a = 1, "immediate"_a = false, "filepath"_a = "",
            "Compile ChucK code and return (success, shred_ids)")

        // Audio processing method
        .def("run",
            [](ChucK& self, nb::ndarray<const SAMPLE, nb::ndim<1>, nb::device::cpu> input,
               nb::ndarray<SAMPLE, nb::ndim<1>, nb::device::cpu, nb::c_contig> output,
               t_CKINT num_frames) {
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
}
