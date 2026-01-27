// numchuck web server module
// Provides HTTP/WebSocket server for browser-based ChucK IDE
//
// Uses Mongoose (https://mongoose.ws) - embedded web server library

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/function.h>

#include "mongoose.h"

#include <atomic>
#include <mutex>
#include <thread>
#include <queue>
#include <string>
#include <vector>
#include <functional>
#include <condition_variable>

namespace nb = nanobind;

// Forward declarations
class WebServer;

// Thread-safe message queue for WebSocket broadcasts
class MessageQueue {
public:
    void push(const std::string& msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(msg);
    }

    bool pop(std::string& msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (queue_.empty()) return false;
        msg = queue_.front();
        queue_.pop();
        return true;
    }

    bool empty() {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }

private:
    std::queue<std::string> queue_;
    std::mutex mutex_;
};

// WebSocket connection tracker
class WebSocketClients {
public:
    void add(struct mg_connection* c) {
        std::lock_guard<std::mutex> lock(mutex_);
        clients_.push_back(c);
    }

    void remove(struct mg_connection* c) {
        std::lock_guard<std::mutex> lock(mutex_);
        clients_.erase(
            std::remove(clients_.begin(), clients_.end(), c),
            clients_.end()
        );
    }

    void broadcast(const std::string& msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto* c : clients_) {
            mg_ws_send(c, msg.c_str(), msg.size(), WEBSOCKET_OP_TEXT);
        }
    }

    size_t count() {
        std::lock_guard<std::mutex> lock(mutex_);
        return clients_.size();
    }

private:
    std::vector<struct mg_connection*> clients_;
    std::mutex mutex_;
};

// Global server instance pointer (for event handler callback)
static WebServer* g_server = nullptr;

class WebServer {
public:
    WebServer() : running_(false), started_successfully_(false), port_(8080) {}

    ~WebServer() {
        stop();
    }

    void set_port(int port) {
        port_ = port;
    }

    int get_port() const {
        return port_;
    }

    void set_static_dir(const std::string& dir) {
        static_dir_ = dir;
    }

    const std::string& get_static_dir() const {
        return static_dir_;
    }

    // Set callback for handling API requests (called from Python)
    void set_api_handler(std::function<std::string(const std::string&, const std::string&, const std::string&)> handler) {
        std::lock_guard<std::mutex> lock(handler_mutex_);
        api_handler_ = handler;
    }

    // Broadcast message to all WebSocket clients
    void broadcast(const std::string& msg) {
        broadcast_queue_.push(msg);
    }

    // Start the server in a background thread
    bool start() {
        if (running_) return false;

        g_server = this;
        running_ = true;
        started_successfully_ = false;

        server_thread_ = std::thread([this]() {
            run_server();
        });

        // Wait for the server to actually bind (or fail)
        {
            std::unique_lock<std::mutex> lock(start_mutex_);
            start_cv_.wait_for(lock, std::chrono::seconds(5), [this]() {
                return started_successfully_ || !running_;
            });
        }

        if (!started_successfully_) {
            // Bind failed - clean up
            if (server_thread_.joinable()) {
                server_thread_.join();
            }
            g_server = nullptr;
            return false;
        }

        return true;
    }

    // Stop the server
    void stop() {
        if (!running_) return;

        running_ = false;
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
        g_server = nullptr;

        // Clear the API handler to release Python callback reference
        {
            std::lock_guard<std::mutex> lock(handler_mutex_);
            api_handler_ = nullptr;
        }
    }

    bool is_running() const {
        return running_;
    }

    size_t client_count() const {
        return ws_clients_.count();
    }

    // Called from event handler
    void handle_event(struct mg_connection* c, int ev, void* ev_data) {
        if (ev == MG_EV_HTTP_MSG) {
            struct mg_http_message* hm = (struct mg_http_message*)ev_data;
            handle_http(c, hm);
        } else if (ev == MG_EV_WS_OPEN) {
            ws_clients_.add(c);
        } else if (ev == MG_EV_WS_MSG) {
            struct mg_ws_message* wm = (struct mg_ws_message*)ev_data;
            handle_websocket(c, wm);
        } else if (ev == MG_EV_CLOSE) {
            if (c->is_websocket) {
                ws_clients_.remove(c);
            }
        }
    }

private:
    void run_server() {
        struct mg_mgr mgr;
        mg_mgr_init(&mgr);

        std::string listen_addr = "http://0.0.0.0:" + std::to_string(port_);

        struct mg_connection* c = mg_http_listen(&mgr, listen_addr.c_str(), event_handler, nullptr);
        if (c == nullptr) {
            mg_mgr_free(&mgr);
            running_ = false;
            started_successfully_ = false;
            start_cv_.notify_all();
            return;
        }

        // Signal that we've started successfully
        started_successfully_ = true;
        start_cv_.notify_all();

        while (running_) {
            mg_mgr_poll(&mgr, 100);

            // Process broadcast queue
            std::string msg;
            while (broadcast_queue_.pop(msg)) {
                ws_clients_.broadcast(msg);
            }
        }

        mg_mgr_free(&mgr);
    }

    static void event_handler(struct mg_connection* c, int ev, void* ev_data, void* fn_data) {
        (void)fn_data;  // unused
        if (g_server) {
            g_server->handle_event(c, ev, ev_data);
        }
    }

    void handle_http(struct mg_connection* c, struct mg_http_message* hm) {
        std::string uri(hm->uri.ptr, hm->uri.len);
        std::string method(hm->method.ptr, hm->method.len);

        // WebSocket upgrade
        if (mg_match(hm->uri, mg_str("/ws"), nullptr)) {
            mg_ws_upgrade(c, hm, nullptr);
            return;
        }

        // API endpoints
        if (uri.rfind("/api/", 0) == 0) {
            // Handle empty body (ptr might be nullptr)
            std::string body;
            if (hm->body.ptr != nullptr && hm->body.len > 0) {
                body = std::string(hm->body.ptr, hm->body.len);
            }
            std::string response;

            {
                std::lock_guard<std::mutex> lock(handler_mutex_);
                if (api_handler_) {
                    // Release GIL for Python callback
                    nb::gil_scoped_acquire gil;
                    try {
                        response = api_handler_(method, uri, body);
                    } catch (const std::exception& e) {
                        response = "{\"error\": \"" + std::string(e.what()) + "\"}";
                        mg_http_reply(c, 500, "Content-Type: application/json\r\n", "%s", response.c_str());
                        return;
                    }
                } else {
                    response = "{\"error\": \"No API handler configured\"}";
                    mg_http_reply(c, 500, "Content-Type: application/json\r\n", "%s", response.c_str());
                    return;
                }
            }

            mg_http_reply(c, 200, "Content-Type: application/json\r\n", "%s", response.c_str());
            return;
        }

        // Serve static files
        if (!static_dir_.empty()) {
            struct mg_http_serve_opts opts = {};
            opts.root_dir = static_dir_.c_str();
            opts.ssi_pattern = nullptr;
            mg_http_serve_dir(c, hm, &opts);
        } else {
            // Serve embedded minimal page if no static dir
            serve_embedded_page(c, hm);
        }
    }

    void handle_websocket(struct mg_connection* c, struct mg_ws_message* wm) {
        std::string msg;
        if (wm->data.ptr != nullptr && wm->data.len > 0) {
            msg = std::string(wm->data.ptr, wm->data.len);
        }

        // Handle WebSocket message via API handler
        std::string response;
        {
            std::lock_guard<std::mutex> lock(handler_mutex_);
            if (api_handler_) {
                nb::gil_scoped_acquire gil;
                try {
                    response = api_handler_("WS", "/ws", msg);
                } catch (const std::exception& e) {
                    response = "{\"error\": \"" + std::string(e.what()) + "\"}";
                }
            }
        }

        if (!response.empty()) {
            mg_ws_send(c, response.c_str(), response.size(), WEBSOCKET_OP_TEXT);
        }
    }

    void serve_embedded_page(struct mg_connection* c, struct mg_http_message* hm) {
        std::string uri(hm->uri.ptr, hm->uri.len);

        if (uri == "/" || uri == "/index.html") {
            const char* html = R"HTML(<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>numchuck Web IDE</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
        header { background: #2d2d2d; padding: 10px 20px; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid #404040; }
        header h1 { font-size: 18px; color: #4fc3f7; }
        .status { padding: 5px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .status.running { background: #4caf50; color: white; }
        .status.stopped { background: #f44336; color: white; }
        .toolbar { display: flex; gap: 8px; margin-left: auto; }
        .toolbar button { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
        .btn-primary { background: #4caf50; color: white; }
        .btn-primary:hover { background: #45a049; }
        .btn-danger { background: #f44336; color: white; }
        .btn-danger:hover { background: #d32f2f; }
        .btn-secondary { background: #555; color: white; }
        .btn-secondary:hover { background: #666; }
        main { flex: 1; display: flex; overflow: hidden; }
        .editor-panel { flex: 1; display: flex; flex-direction: column; border-right: 1px solid #404040; }
        .editor-header { background: #2d2d2d; padding: 8px 15px; font-size: 13px; color: #888; border-bottom: 1px solid #404040; }
        .editor-container { flex: 1; overflow: hidden; }
        .CodeMirror { height: 100% !important; font-size: 14px; line-height: 1.5; }
        .sidebar { width: 350px; display: flex; flex-direction: column; }
        .panel { flex: 1; display: flex; flex-direction: column; border-bottom: 1px solid #404040; }
        .panel:last-child { border-bottom: none; }
        .panel-header { background: #2d2d2d; padding: 8px 15px; font-size: 13px; font-weight: 600; color: #4fc3f7; border-bottom: 1px solid #404040; }
        .panel-content { flex: 1; overflow-y: auto; padding: 10px; }
        #shreds-list { list-style: none; }
        #shreds-list li { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: #2d2d2d; border-radius: 4px; margin-bottom: 5px; }
        #shreds-list .shred-id { color: #4fc3f7; font-weight: 600; width: 30px; }
        #shreds-list .shred-name { flex: 1; color: #d4d4d4; }
        #shreds-list .shred-time { color: #888; font-size: 12px; margin-right: 10px; }
        #shreds-list .shred-remove { background: #f44336; color: white; border: none; border-radius: 50%; width: 22px; height: 22px; cursor: pointer; font-size: 14px; line-height: 1; }
        #console { font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
        .console-line { padding: 2px 0; }
        .console-line.error { color: #f44336; }
        .console-line.info { color: #4fc3f7; }
        .empty-state { color: #666; font-style: italic; text-align: center; padding: 20px; }
        /* ChucK-specific syntax colors */
        .cm-s-material-darker .cm-chuck-ugen { color: #82aaff; }
        .cm-s-material-darker .cm-chuck-time { color: #c792ea; }
        .cm-s-material-darker .cm-chuck-operator { color: #89ddff; }
        .cm-s-material-darker .cm-chuck-keyword { color: #c792ea; }
        .cm-s-material-darker .cm-chuck-type { color: #ffcb6b; }
        .cm-s-material-darker .cm-chuck-builtin { color: #82aaff; }
    </style>
</head>
<body>
    <header>
        <h1>numchuck</h1>
        <span id="status" class="status stopped">Stopped</span>
        <div class="toolbar">
            <button id="btn-start" class="btn-primary" onclick="startAudio()">Start Audio</button>
            <button id="btn-stop" class="btn-danger" onclick="stopAudio()" style="display:none">Stop Audio</button>
            <button class="btn-primary" onclick="sporkCode()">Spork</button>
            <button class="btn-secondary" onclick="clearAll()">Clear All</button>
        </div>
    </header>
    <main>
        <div class="editor-panel">
            <div class="editor-header">untitled.ck</div>
            <div class="editor-container">
                <textarea id="editor">// numchuck Web IDE
// Write ChucK code here and click Spork to run

SinOsc s => dac;
440 => s.freq;
0.5 => s.gain;

<<< "Hello from numchuck!" >>>;

1::second => now;
</textarea>
            </div>
        </div>
        <div class="sidebar">
            <div class="panel">
                <div class="panel-header">SHREDS</div>
                <div class="panel-content">
                    <ul id="shreds-list">
                        <li class="empty-state">No shreds running</li>
                    </ul>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">CONSOLE</div>
                <div class="panel-content" id="console">
                    <div class="console-line info">numchuck Web IDE ready</div>
                </div>
            </div>
        </div>
    </main>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/mode/simple.min.js"></script>
    <script>
        // Define ChucK syntax mode
        CodeMirror.defineSimpleMode("chuck", {
            start: [
                {regex: /\/\/.*/, token: "comment"},
                {regex: /\/\*/, token: "comment", next: "comment"},
                {regex: /<<<.*?>>>/, token: "string-2"},
                {regex: /"(?:[^\\]|\\.)*?(?:"|$)/, token: "string"},
                {regex: /'(?:[^\\]|\\.)*?(?:'|$)/, token: "string"},
                {regex: /\b(if|else|while|for|until|repeat|break|continue|return|class|extends|public|private|static|pure|function|fun|spork|new|null|NULL|true|false|maybe|this|super|me|now|dac|adc|blackhole)\b/, token: "chuck-keyword"},
                {regex: /\b(int|float|time|dur|void|string|complex|polar|vec3|vec4|Object|Event|UGen|UAna|Shred|Thread|Class|IO|FileIO|OscIn|OscOut|OscMsg|Hid|HidMsg|SerialIO|MidiIn|MidiOut|MidiMsg|MidiFileIn)\b/, token: "chuck-type"},
                {regex: /\b(SinOsc|TriOsc|SqrOsc|SawOsc|PulseOsc|Phasor|Noise|Impulse|Step|Gain|Pan2|Mix2|dac|adc|blackhole|Envelope|ADSR|Delay|DelayL|DelayA|Echo|JCRev|NRev|PRCRev|Chorus|Modulate|PitShift|SubNoise|Blit|BlitSaw|BlitSquare|WvIn|WvOut|WvOut2|SndBuf|SndBuf2|LiSa|Dyno|LPF|HPF|BPF|BRF|ResonZ|BiQuad|OnePole|TwoPole|OneZero|TwoZero|PoleZero|FilterBasic|Mandolin|Moog|Saxofony|Shakers|Sitar|StifKarp|BeeThree|FM|FMVoices|HevyMetl|PercFlut|Rhodey|TubeBell|Wurley|VoicForm|KrstlChr|Gen5|Gen7|Gen9|Gen10|Gen17|CurveTable|WarpTable|Chugraph|Chugen)\b/, token: "chuck-ugen"},
                {regex: /\b(samp|ms|second|minute|hour|day|week)\b/, token: "chuck-time"},
                {regex: /\b(Std|Math|Machine|RegEx|Shred|me|Type|Object|string|IO)\b/, token: "chuck-builtin"},
                {regex: /=>|=<|@=>|=\^|!=>|\+=>|-=>|\*=>|\/=>|%=>|&=>|\|=>|\^=>|>>=>|<<=>|-->|--<|<--|>--/, token: "chuck-operator"},
                {regex: /[-+\/*=<>!&|%^~]+/, token: "operator"},
                {regex: /\b\d+\.?\d*([eE][-+]?\d+)?\b/, token: "number"},
                {regex: /\b0x[0-9a-fA-F]+\b/, token: "number"},
                {regex: /[a-zA-Z_]\w*/, token: "variable"},
                {regex: /[{}\[\]();,.]/, token: "punctuation"}
            ],
            comment: [
                {regex: /.*?\*\//, token: "comment", next: "start"},
                {regex: /.*/, token: "comment"}
            ],
            meta: {lineComment: "//", blockCommentStart: "/*", blockCommentEnd: "*/"}
        });

        let editor;
        let ws;
        let audioRunning = false;

        // Initialize CodeMirror
        document.addEventListener('DOMContentLoaded', function() {
            editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
                mode: 'chuck',
                theme: 'material-darker',
                lineNumbers: true,
                indentUnit: 4,
                tabSize: 4,
                indentWithTabs: false,
                lineWrapping: false,
                matchBrackets: true,
                autoCloseBrackets: true,
                extraKeys: {
                    'Cmd-Enter': function(cm) { sporkCode(); },
                    'Ctrl-Enter': function(cm) { sporkCode(); }
                }
            });
        });

        function getCode() {
            return editor ? editor.getValue() : document.getElementById('editor').value;
        }

        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = () => log('Connected to server', 'info');
            ws.onclose = () => { log('Disconnected', 'error'); setTimeout(connect, 2000); };
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
        }

        function handleMessage(msg) {
            if (msg.type === 'console') {
                log(msg.text, msg.level || 'info');
            } else if (msg.type === 'shreds') {
                updateShreds(msg.shreds);
            } else if (msg.type === 'audio_status') {
                setAudioStatus(msg.running);
            } else if (msg.type === 'status') {
                updateShreds(msg.shreds || []);
                setAudioStatus(msg.audio_running);
            }
        }

        function log(text, level = 'info') {
            const consoleEl = document.getElementById('console');
            const line = document.createElement('div');
            line.className = 'console-line ' + level;
            line.textContent = text;
            consoleEl.appendChild(line);
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        function updateShreds(shreds) {
            const list = document.getElementById('shreds-list');
            if (shreds.length === 0) {
                list.innerHTML = '<li class="empty-state">No shreds running</li>';
                return;
            }
            list.innerHTML = shreds.map(s => `
                <li>
                    <span class="shred-id">${s.id}</span>
                    <span class="shred-name">${s.name || 'code'}</span>
                    <span class="shred-time">${s.time || ''}</span>
                    <button class="shred-remove" onclick="removeShred(${s.id})">-</button>
                </li>
            `).join('');
        }

        function setAudioStatus(running) {
            audioRunning = running;
            const status = document.getElementById('status');
            const btnStart = document.getElementById('btn-start');
            const btnStop = document.getElementById('btn-stop');
            if (running) {
                status.textContent = 'Running';
                status.className = 'status running';
                btnStart.style.display = 'none';
                btnStop.style.display = 'inline-block';
            } else {
                status.textContent = 'Stopped';
                status.className = 'status stopped';
                btnStart.style.display = 'inline-block';
                btnStop.style.display = 'none';
            }
        }

        async function apiCall(method, endpoint, body = null) {
            const opts = { method, headers: { 'Content-Type': 'application/json' } };
            if (body) opts.body = JSON.stringify(body);
            const res = await fetch('/api' + endpoint, opts);
            return res.json();
        }

        async function sporkCode() {
            const code = getCode();
            const result = await apiCall('POST', '/compile', { code });
            if (result.success) {
                log('Sporked shred ' + result.shred_ids.join(', '), 'info');
            } else {
                log('Error: ' + (result.error || 'Compilation failed'), 'error');
            }
        }

        async function removeShred(id) {
            await apiCall('DELETE', '/shred/' + id);
        }

        async function clearAll() {
            await apiCall('POST', '/clear');
            log('Cleared all shreds', 'info');
        }

        async function startAudio() {
            const result = await apiCall('POST', '/audio/start');
            if (!result.success) log('Failed to start audio: ' + result.error, 'error');
        }

        async function stopAudio() {
            const result = await apiCall('POST', '/audio/stop');
            if (!result.success) log('Failed to stop audio: ' + result.error, 'error');
        }

        connect();
        // Poll status every 2 seconds
        setInterval(async () => {
            try {
                const status = await apiCall('GET', '/status');
                handleMessage({ type: 'status', ...status });
            } catch (e) {}
        }, 2000);
    </script>
</body>
</html>)HTML";
            mg_http_reply(c, 200, "Content-Type: text/html\r\n", "%s", html);
        } else {
            mg_http_reply(c, 404, "", "Not Found");
        }
    }

    std::atomic<bool> running_;
    std::atomic<bool> started_successfully_;
    int port_;
    std::string static_dir_;
    std::thread server_thread_;

    std::function<std::string(const std::string&, const std::string&, const std::string&)> api_handler_;
    std::mutex handler_mutex_;

    // For signaling successful start
    std::mutex start_mutex_;
    std::condition_variable start_cv_;

    MessageQueue broadcast_queue_;
    mutable WebSocketClients ws_clients_;
};


NB_MODULE(_web, m) {
    m.doc() = "numchuck web server module";

    nb::class_<WebServer>(m, "WebServer")
        .def(nb::init<>())
        .def_prop_rw("port", &WebServer::get_port, &WebServer::set_port,
                     "Server port (default: 8080)")
        .def_prop_rw("static_dir", &WebServer::get_static_dir, &WebServer::set_static_dir,
                     "Directory for static files")
        .def("set_api_handler", &WebServer::set_api_handler,
             "Set the API request handler callback")
        .def("broadcast", &WebServer::broadcast,
             "Broadcast message to all WebSocket clients")
        .def("start", &WebServer::start,
             "Start the web server in background thread")
        .def("stop", &WebServer::stop,
             "Stop the web server")
        .def_prop_ro("is_running", &WebServer::is_running,
                     "Check if server is running")
        .def_prop_ro("client_count", &WebServer::client_count,
                     "Number of connected WebSocket clients");
}
