// numchuck web server module
// Provides HTTP/WebSocket server for browser-based ChucK IDE
//
// Uses Mongoose (https://mongoose.ws) - embedded web server library

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
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
    WebServer() : running_(false), started_successfully_(false), port_(numchuck::DEFAULT_WEB_PORT) {}

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
            start_cv_.wait_for(lock, std::chrono::seconds(numchuck::SERVER_STARTUP_TIMEOUT_SECS), [this]() {
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
        // Fallback when no static_dir is set - return 404
        // Static files are served by mongoose when static_dir is configured
        mg_http_reply(c, 404, "", "Not Found - no static directory configured");
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
