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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a1a; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }

        /* Header / Toolbar */
        header { background: #252525; padding: 8px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #333; }
        .logo { display: flex; align-items: center; gap: 8px; }
        .logo svg { width: 24px; height: 24px; }
        .logo span { font-size: 16px; font-weight: 600; color: #4fc3f7; }

        /* Status indicator */
        .status-badge { padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .status-badge.running { background: #2e7d32; color: #fff; }
        .status-badge.stopped { background: #c62828; color: #fff; }
        .status-badge::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }

        /* Toolbar buttons */
        .toolbar { display: flex; gap: 8px; margin-left: 20px; }
        .tool-btn { width: 42px; height: 42px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform 0.1s, box-shadow 0.2s; }
        .tool-btn:hover { transform: scale(1.05); }
        .tool-btn:active { transform: scale(0.95); }
        .tool-btn svg { width: 20px; height: 20px; fill: white; }
        .tool-btn.play { background: linear-gradient(135deg, #43a047, #2e7d32); }
        .tool-btn.replace { background: linear-gradient(135deg, #1e88e5, #1565c0); }
        .tool-btn.stop { background: linear-gradient(135deg, #fb8c00, #ef6c00); }
        .tool-btn.clear { background: linear-gradient(135deg, #e53935, #c62828); }
        .tool-btn[disabled] { opacity: 0.5; cursor: not-allowed; transform: none; }

        .spacer { flex: 1; }
        .title { font-size: 14px; color: #888; }

        /* Main layout */
        main { flex: 1; display: flex; overflow: hidden; }

        /* File explorer sidebar */
        .file-sidebar { width: 180px; background: #1e1e1e; border-right: 1px solid #333; display: flex; flex-direction: column; }
        .sidebar-header { padding: 10px 12px; font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #333; }
        .file-list { flex: 1; overflow-y: auto; padding: 8px 0; }
        .file-item { padding: 6px 12px; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 8px; color: #ccc; }
        .file-item:hover { background: #2a2a2a; }
        .file-item.active { background: #333; color: #fff; }
        .file-item svg { width: 16px; height: 16px; fill: #888; }

        /* Editor area */
        .editor-area { flex: 1; display: flex; flex-direction: column; }
        .editor-tabs { background: #252525; display: flex; border-bottom: 1px solid #333; }
        .editor-tab { padding: 10px 20px; font-size: 13px; color: #888; cursor: pointer; border-right: 1px solid #333; display: flex; align-items: center; gap: 8px; }
        .editor-tab.active { background: #1a1a1a; color: #fff; }
        .editor-tab svg { width: 14px; height: 14px; fill: currentColor; }
        .editor-container { flex: 1; overflow: hidden; }
        .CodeMirror { height: 100% !important; font-size: 14px; line-height: 1.6; background: #1a1a1a; }

        /* Right sidebar */
        .right-sidebar { width: 320px; display: flex; flex-direction: column; border-left: 1px solid #333; background: #1e1e1e; }

        /* Shred panel */
        .shred-panel { height: 200px; display: flex; flex-direction: column; border-bottom: 1px solid #333; }
        .panel-header { padding: 10px 12px; font-size: 11px; font-weight: 600; color: #4fc3f7; text-transform: uppercase; letter-spacing: 0.5px; background: #252525; border-bottom: 1px solid #333; }
        .shred-table { flex: 1; overflow-y: auto; }
        .shred-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .shred-table th { text-align: left; padding: 8px 10px; color: #888; font-weight: 500; border-bottom: 1px solid #333; background: #222; position: sticky; top: 0; }
        .shred-table td { padding: 8px 10px; border-bottom: 1px solid #2a2a2a; }
        .shred-table tr:hover td { background: #252525; }
        .shred-id { color: #4fc3f7; font-weight: 600; }
        .shred-name { color: #e0e0e0; }
        .shred-time { color: #888; font-family: monospace; }
        .remove-btn { width: 24px; height: 24px; border-radius: 50%; border: none; background: #c62828; color: white; cursor: pointer; font-size: 16px; line-height: 1; display: flex; align-items: center; justify-content: center; }
        .remove-btn:hover { background: #e53935; }
        .empty-row td { color: #666; font-style: italic; text-align: center; padding: 20px; }

        /* Console panel */
        .console-panel { flex: 1; display: flex; flex-direction: column; min-height: 0; }
        .panel-tabs { display: flex; background: #252525; border-bottom: 1px solid #333; }
        .panel-tab { padding: 8px 16px; font-size: 11px; font-weight: 600; color: #888; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid transparent; }
        .panel-tab:hover { color: #bbb; }
        .panel-tab.active { color: #4fc3f7; border-bottom-color: #4fc3f7; }
        .console-content { flex: 1; overflow-y: auto; padding: 10px; font-family: 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 12px; line-height: 1.5; }
        .console-line { padding: 2px 0; white-space: pre-wrap; word-break: break-all; }
        .console-line.error { color: #ef5350; }
        .console-line.info { color: #4fc3f7; }
        .console-line.warn { color: #ffb74d; }
        .console-line.vm { color: #81c784; }

        /* Keyboard shortcut hint */
        .shortcut-hint { font-size: 11px; color: #666; margin-left: 8px; }
        .shortcut-hint kbd { background: #333; padding: 2px 6px; border-radius: 3px; font-family: inherit; }

        /* ChucK syntax colors */
        .cm-s-material-darker .cm-chuck-ugen { color: #82aaff; }
        .cm-s-material-darker .cm-chuck-time { color: #c792ea; }
        .cm-s-material-darker .cm-chuck-operator { color: #89ddff; font-weight: bold; }
        .cm-s-material-darker .cm-chuck-keyword { color: #c792ea; }
        .cm-s-material-darker .cm-chuck-type { color: #ffcb6b; }
        .cm-s-material-darker .cm-chuck-builtin { color: #82aaff; }
        .cm-s-material-darker .cm-string-2 { color: #c3e88d; } /* <<< >>> */
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <svg viewBox="0 0 24 24"><path fill="#4fc3f7" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            <span>numchuck</span>
        </div>
        <div id="status" class="status-badge stopped">Stopped</div>

        <div class="toolbar">
            <button class="tool-btn play" onclick="sporkCode()" title="Spork Code (Cmd+Enter)">
                <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            </button>
            <button class="tool-btn replace" onclick="replaceShred()" title="Replace Last Shred">
                <svg viewBox="0 0 24 24"><path d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></svg>
            </button>
            <button class="tool-btn stop" onclick="clearAll()" title="Remove All Shreds">
                <svg viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
            </button>
        </div>

        <span class="shortcut-hint"><kbd>Cmd</kbd>+<kbd>Enter</kbd> to spork</span>
        <div class="spacer"></div>

        <button id="btn-audio" class="tool-btn play" onclick="toggleAudio()" title="Start/Stop Audio">
            <svg id="audio-icon" viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
        </button>
    </header>

    <main>
        <div class="file-sidebar">
            <div class="sidebar-header">File Explorer</div>
            <div class="file-list">
                <div class="file-item active">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>
                    untitled.ck
                </div>
            </div>
        </div>

        <div class="editor-area">
            <div class="editor-tabs">
                <div class="editor-tab active">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>
                    untitled.ck
                </div>
            </div>
            <div class="editor-container">
                <textarea id="editor">// numchuck Web IDE
// Press Cmd+Enter (Mac) or Ctrl+Enter (Windows/Linux) to spork

SinOsc s => dac;
440 => s.freq;
0.5 => s.gain;

<<< "Hello from numchuck!" >>>;

1::second => now;
</textarea>
            </div>
        </div>

        <div class="right-sidebar">
            <div class="shred-panel">
                <div class="panel-header">Shreds</div>
                <div class="shred-table">
                    <table>
                        <thead>
                            <tr>
                                <th style="width:50px">ID</th>
                                <th>Code</th>
                                <th style="width:60px">Time</th>
                                <th style="width:40px"></th>
                            </tr>
                        </thead>
                        <tbody id="shreds-body">
                            <tr class="empty-row"><td colspan="4">No shreds running</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="console-panel">
                <div class="panel-tabs">
                    <div class="panel-tab active">Console</div>
                </div>
                <div class="console-content" id="console">
                    <div class="console-line info">numchuck Web IDE ready</div>
                </div>
            </div>
        </div>
    </main>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/mode/simple.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/matchbrackets.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/closebrackets.min.js"></script>
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
                {regex: /\b(SinOsc|TriOsc|SqrOsc|SawOsc|PulseOsc|Phasor|Noise|Impulse|Step|Gain|Pan2|Mix2|Envelope|ADSR|Delay|DelayL|DelayA|Echo|JCRev|NRev|PRCRev|Chorus|Modulate|PitShift|SubNoise|Blit|BlitSaw|BlitSquare|WvIn|WvOut|WvOut2|SndBuf|SndBuf2|LiSa|Dyno|LPF|HPF|BPF|BRF|ResonZ|BiQuad|OnePole|TwoPole|OneZero|TwoZero|PoleZero|FilterBasic|Mandolin|Moog|Saxofony|Shakers|Sitar|StifKarp|BeeThree|FM|FMVoices|HevyMetl|PercFlut|Rhodey|TubeBell|Wurley|VoicForm|KrstlChr|Gen5|Gen7|Gen9|Gen10|Gen17|CurveTable|WarpTable|Chugraph|Chugen)\b/, token: "chuck-ugen"},
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
        let lastShredId = null;

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
            // Limit console lines
            while (consoleEl.children.length > 200) {
                consoleEl.removeChild(consoleEl.firstChild);
            }
        }

        function updateShreds(shreds) {
            const tbody = document.getElementById('shreds-body');
            if (shreds.length === 0) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No shreds running</td></tr>';
                lastShredId = null;
                return;
            }
            tbody.innerHTML = shreds.map(s => `
                <tr>
                    <td class="shred-id">${s.id}</td>
                    <td class="shred-name">${s.name || 'code'}</td>
                    <td class="shred-time">${s.time || '00:00'}</td>
                    <td><button class="remove-btn" onclick="removeShred(${s.id})">-</button></td>
                </tr>
            `).join('');
            // Track last shred for replace
            if (shreds.length > 0) {
                lastShredId = shreds[shreds.length - 1].id;
            }
        }

        function setAudioStatus(running) {
            audioRunning = running;
            const status = document.getElementById('status');
            const audioBtn = document.getElementById('btn-audio');
            const audioIcon = document.getElementById('audio-icon');
            if (running) {
                status.textContent = 'Running';
                status.className = 'status-badge running';
                audioBtn.classList.remove('play');
                audioBtn.classList.add('stop');
                audioIcon.innerHTML = '<path d="M6 6h12v12H6z"/>';
            } else {
                status.textContent = 'Stopped';
                status.className = 'status-badge stopped';
                audioBtn.classList.remove('stop');
                audioBtn.classList.add('play');
                audioIcon.innerHTML = '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>';
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
                log('[chuck]: sporking incoming shred: ' + result.shred_ids.join(', ') + ' (code)...', 'vm');
            } else {
                log('Error: ' + (result.error || 'Compilation failed'), 'error');
            }
        }

        async function replaceShred() {
            if (lastShredId) {
                await removeShred(lastShredId);
            }
            await sporkCode();
        }

        async function removeShred(id) {
            log('[chuck]: removing shred: ' + id + '...', 'vm');
            await apiCall('DELETE', '/shred/' + id);
        }

        async function clearAll() {
            log('[chuck]: removing all shreds...', 'vm');
            await apiCall('POST', '/clear');
        }

        async function toggleAudio() {
            if (audioRunning) {
                const result = await apiCall('POST', '/audio/stop');
                if (!result.success) log('Failed to stop audio: ' + result.error, 'error');
            } else {
                const result = await apiCall('POST', '/audio/start');
                if (!result.success) log('Failed to start audio: ' + result.error, 'error');
            }
        }

        connect();
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
