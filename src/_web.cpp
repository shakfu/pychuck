// numchuck web server module
// Provides HTTP/WebSocket server for browser-based ChucK IDE
//
// Uses Mongoose (https://mongoose.ws) - embedded web server library
//
// Trust model
// -----------
// The API this serves is arbitrary ChucK execution, which is arbitrary code
// execution: ChucK's standard library includes FileIO. So the server is only
// as safe as the reach of whoever can talk to it. Three things enforce that:
//
//   1. The listen address is chosen by the caller and defaults to loopback
//      (see WebChuckServer in numchuck/web/__init__.py). Nothing here binds
//      0.0.0.0 unless asked to.
//   2. A bearer token, when set, is required on every /api/ request and on the
//      WebSocket upgrade. The Python layer makes it mandatory for any
//      non-loopback bind.
//   3. Origin is checked against Host on every request that carries one. A
//      browser cannot forge either, so a page on another origin cannot reach
//      this server even when it runs on the victim's own loopback -- which is
//      what makes the WebSocket upgrade safe, since WebSockets are not subject
//      to the same-origin policy on their own.

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/function.h>

#include "mongoose.h"
#include "constants.h"

#include <algorithm>
#include <atomic>
#include <mutex>
#include <thread>
#include <queue>
#include <string>
#include <vector>
#include <functional>
#include <condition_variable>

namespace nb = nanobind;

namespace {

// Escape a string for embedding in a JSON string literal. Error text reaches
// the client inside a JSON body, and an exception message containing a quote
// would otherwise produce a document the browser cannot parse.
std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 16);
    for (unsigned char ch : s) {
        switch (ch) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (ch < 0x20) {
                    char buf[7];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", ch);
                    out += buf;
                } else {
                    out += static_cast<char>(ch);
                }
        }
    }
    return out;
}

std::string json_error(const std::string& message) {
    return "{\"error\": \"" + json_escape(message) + "\"}";
}

// Sent on everything. Without a Cache-Control header a browser falls back to
// heuristic caching (RFC 9111 4.2.2) and may reuse a response without asking,
// which on a loopback port is a real hazard: every local tool competes for
// 127.0.0.1:8080, so a page cached for a *different* server on that origin gets
// served in place of this one. Observed with Safari showing a llama.cpp UI for
// numchuck's port. VM state is not cacheable either, so this applies to the API
// as much as to the documents.
constexpr const char* NO_CACHE = "Cache-Control: no-store\r\n";

const char* JSON_HEADERS =
    "Content-Type: application/json\r\n"
    "Cache-Control: no-store\r\n";

// Compare without an early exit on the first differing byte, so a caller
// cannot recover the token one character at a time from response latency.
bool tokens_match(const std::string& expected, const std::string& given) {
    if (expected.size() != given.size()) return false;
    unsigned char diff = 0;
    for (size_t i = 0; i < expected.size(); i++) {
        diff |= static_cast<unsigned char>(expected[i] ^ given[i]);
    }
    return diff == 0;
}

std::string to_string(struct mg_str s) {
    return (s.ptr != nullptr && s.len > 0) ? std::string(s.ptr, s.len) : std::string();
}

// Strip the scheme from an Origin so it can be compared against a Host header,
// which never carries one. "http://localhost:8080" -> "localhost:8080".
std::string origin_authority(const std::string& origin) {
    size_t sep = origin.find("://");
    return (sep == std::string::npos) ? origin : origin.substr(sep + 3);
}

}  // namespace

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

class WebServer {
public:
    // The handler answers with (http_status, json_body).
    using ApiHandler = std::function<std::pair<int, std::string>(
        const std::string&, const std::string&, const std::string&)>;

    WebServer()
        : running_(false), started_successfully_(false),
          port_(numchuck::DEFAULT_WEB_PORT), host_("127.0.0.1") {}

    ~WebServer() {
        stop();
    }

    void set_port(int port) {
        port_ = port;
    }

    int get_port() const {
        return port_;
    }

    // Listen address. Defaults to loopback; the caller must opt in to anything
    // wider, and the Python layer requires a token when it does.
    void set_host(const std::string& host) {
        host_ = host;
    }

    const std::string& get_host() const {
        return host_;
    }

    void set_auth_token(const std::string& token) {
        std::lock_guard<std::mutex> lock(auth_mutex_);
        auth_token_ = token;
    }

    std::string get_auth_token() const {
        std::lock_guard<std::mutex> lock(auth_mutex_);
        return auth_token_;
    }

    void set_static_dir(const std::string& dir) {
        static_dir_ = dir;
    }

    const std::string& get_static_dir() const {
        return static_dir_;
    }

    // Set callback for handling API requests (called from Python)
    void set_api_handler(ApiHandler handler) {
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

        running_ = true;
        started_successfully_ = false;

        server_thread_ = std::thread([this]() {
            run_server();
        });

        // Wait for the server to actually bind (or fail). The wait blocks on a
        // condition variable the server thread signals, so the GIL has to go --
        // see join_server_thread() for the same reasoning.
        bool ok;
        {
            nb::gil_scoped_release unlocked;   // see join_server_thread()
            std::unique_lock<std::mutex> lock(start_mutex_);
            start_cv_.wait_for(lock, std::chrono::seconds(numchuck::SERVER_STARTUP_TIMEOUT_SECS), [this]() {
                return started_successfully_ || !running_;
            });
            ok = started_successfully_;
        }

        if (!ok) {
            // Bind failed - clean up
            join_server_thread();
            running_ = false;
            return false;
        }

        return true;
    }

    // Stop the server
    void stop() {
        if (!running_) return;

        running_ = false;
        join_server_thread();

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
    // Waiting for the server thread with the GIL held is a deadlock: that
    // thread blocks on gil_scoped_acquire before every API callback, so it can
    // never reach the point where it notices running_ == false.
    //
    // Releasing is unconditional because every path that reaches start()/stop()
    // holds the GIL -- the two bound methods and the nanobind type destructor.
    // run_server() never calls either, so the server thread cannot arrive here
    // without it. (PyGILState_Check would make that a runtime check, but it is
    // outside the stable ABI this extension builds against.)
    void join_server_thread() {
        if (!server_thread_.joinable()) return;
        nb::gil_scoped_release unlocked;
        server_thread_.join();
    }

    void run_server() {
        struct mg_mgr mgr;
        mg_mgr_init(&mgr);

        std::string listen_addr = "http://" + host_ + ":" + std::to_string(port_);

        // `this` rides along as fn_data and is copied onto every accepted
        // connection, so the handler reaches the right instance without a
        // process-wide singleton -- two servers in one process work.
        struct mg_connection* c = mg_http_listen(&mgr, listen_addr.c_str(), event_handler, this);
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
            mg_mgr_poll(&mgr, numchuck::WEB_POLL_INTERVAL_MS);

            // Process broadcast queue
            std::string msg;
            while (broadcast_queue_.pop(msg)) {
                ws_clients_.broadcast(msg);
            }
        }

        mg_mgr_free(&mgr);
    }

    static void event_handler(struct mg_connection* c, int ev, void* ev_data, void* fn_data) {
        WebServer* self = static_cast<WebServer*>(fn_data);
        if (self) {
            self->handle_event(c, ev, ev_data);
        }
    }

    // A request from a browser page on another origin. Origin is set by the
    // browser and cannot be overridden by script, and it is sent on WebSocket
    // handshakes as well, so comparing it to Host closes cross-site access
    // without needing to know the deployment's own address.
    bool origin_is_foreign(struct mg_http_message* hm) const {
        struct mg_str* origin = mg_http_get_header(hm, "Origin");
        if (origin == nullptr || origin->len == 0) {
            return false;  // not a browser-initiated request
        }
        struct mg_str* host = mg_http_get_header(hm, "Host");
        if (host == nullptr || host->len == 0) {
            return true;  // HTTP/1.1 requires Host; without it nothing to match
        }
        return origin_authority(to_string(*origin)) != to_string(*host);
    }

    // Bearer token in the Authorization header, or ?token= for the WebSocket
    // handshake, which browsers give no way to add headers to.
    bool token_ok(struct mg_http_message* hm) const {
        std::string expected = get_auth_token();
        if (expected.empty()) return true;

        struct mg_str* auth = mg_http_get_header(hm, "Authorization");
        if (auth != nullptr && auth->len > 0) {
            std::string value = to_string(*auth);
            const std::string prefix = "Bearer ";
            if (value.rfind(prefix, 0) == 0 &&
                tokens_match(expected, value.substr(prefix.size()))) {
                return true;
            }
        }

        char buf[256];
        int n = mg_http_get_var(&hm->query, "token", buf, sizeof(buf));
        if (n > 0 && tokens_match(expected, std::string(buf, static_cast<size_t>(n)))) {
            return true;
        }

        return false;
    }

    // Returns false and answers the connection if the request must not proceed.
    bool authorize(struct mg_connection* c, struct mg_http_message* hm) {
        if (origin_is_foreign(hm)) {
            mg_http_reply(c, 403, JSON_HEADERS, "%s",
                          json_error("Cross-origin request rejected").c_str());
            return false;
        }
        if (!token_ok(hm)) {
            mg_http_reply(c, 401,
                          "Content-Type: application/json\r\n"
                          "Cache-Control: no-store\r\n"
                          "WWW-Authenticate: Bearer\r\n",
                          "%s", json_error("Missing or invalid auth token").c_str());
            return false;
        }
        return true;
    }

    void handle_http(struct mg_connection* c, struct mg_http_message* hm) {
        std::string uri = to_string(hm->uri);
        std::string method = to_string(hm->method);

        // WebSocket upgrade
        if (mg_match(hm->uri, mg_str("/ws"), nullptr)) {
            if (!authorize(c, hm)) return;
            mg_ws_upgrade(c, hm, nullptr);
            return;
        }

        // API endpoints
        if (uri.rfind("/api/", 0) == 0) {
            if (!authorize(c, hm)) return;

            // Handle empty body (ptr might be nullptr)
            std::string body = to_string(hm->body);

            int status;
            std::string response;
            {
                // GIL before handler_mutex_, always and everywhere. The handler
                // is a Python callable, so set_api_handler() and the clear in
                // stop() cannot touch it without the GIL -- taking the two in
                // the other order here would let this thread hold the mutex
                // while waiting for the GIL that the assigning thread holds.
                nb::gil_scoped_acquire gil;
                std::lock_guard<std::mutex> lock(handler_mutex_);
                if (!api_handler_) {
                    status = 503;
                    response = json_error("No API handler configured");
                } else {
                    try {
                        std::pair<int, std::string> result = api_handler_(method, uri, body);
                        status = result.first;
                        response = result.second;
                    } catch (const std::exception& e) {
                        status = 500;
                        response = json_error(e.what());
                    }
                }
            }

            mg_http_reply(c, status, JSON_HEADERS, "%s", response.c_str());
            return;
        }

        // Serve static files. Anything under the static root is public by
        // design (it is the IDE's own HTML/JS), so no token is demanded here --
        // but a cross-origin page still must not read it.
        if (origin_is_foreign(hm)) {
            mg_http_reply(c, 403, NO_CACHE, "Forbidden");
            return;
        }
        if (!static_dir_.empty()) {
            struct mg_http_serve_opts opts = {};
            opts.root_dir = static_dir_.c_str();
            opts.ssi_pattern = nullptr;
            opts.extra_headers = NO_CACHE;
            mg_http_serve_dir(c, hm, &opts);
        } else {
            // Serve embedded minimal page if no static dir
            serve_embedded_page(c, hm);
        }
    }

    void handle_websocket(struct mg_connection* c, struct mg_ws_message* wm) {
        // The upgrade was authorized; the socket stays authorized for its life.
        std::string msg;
        if (wm->data.ptr != nullptr && wm->data.len > 0) {
            msg = std::string(wm->data.ptr, wm->data.len);
        }

        // Handle WebSocket message via API handler
        std::string response;
        {
            nb::gil_scoped_acquire gil;   // GIL before handler_mutex_; see handle_http
            std::lock_guard<std::mutex> lock(handler_mutex_);
            if (api_handler_) {
                try {
                    response = api_handler_("WS", "/ws", msg).second;
                } catch (const std::exception& e) {
                    response = json_error(e.what());
                }
            }
        }

        if (!response.empty()) {
            mg_ws_send(c, response.c_str(), response.size(), WEBSOCKET_OP_TEXT);
        }
    }

    void serve_embedded_page(struct mg_connection* c, struct mg_http_message* hm) {
        // Fallback when no static_dir is set - return 404
        // Static files are served by mongoose when static_dir is configured
        (void)hm;
        mg_http_reply(c, 404, NO_CACHE, "Not Found - no static directory configured");
    }

    std::atomic<bool> running_;
    std::atomic<bool> started_successfully_;
    int port_;
    std::string host_;
    std::string static_dir_;
    std::string auth_token_;
    mutable std::mutex auth_mutex_;
    std::thread server_thread_;

    ApiHandler api_handler_;
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
        .def_prop_rw("host", &WebServer::get_host, &WebServer::set_host,
                     "Listen address (default: 127.0.0.1)")
        .def_prop_rw("auth_token", &WebServer::get_auth_token, &WebServer::set_auth_token,
                     "Bearer token required on /api/ and /ws (empty disables auth)")
        .def_prop_rw("static_dir", &WebServer::get_static_dir, &WebServer::set_static_dir,
                     "Directory for static files")
        .def("set_api_handler", &WebServer::set_api_handler,
             "Set the API request handler callback, returning (status, body)")
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
