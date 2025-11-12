from flask import Flask, request, jsonify, Response
import requests, threading, time

app = Flask(__name__)

# --- Backend Servers (your real app servers) ---
SERVERS = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003"
]

HEALTHY_SERVERS = SERVERS.copy()
CURRENT = 0

# --- Background Health Check ---
def check_health():
    """Continuously check backend server health every few seconds."""
    global HEALTHY_SERVERS
    while True:
        healthy = []
        for server in SERVERS:
            try:
                r = requests.get(f"{server}/health", timeout=2)
                if r.status_code == 200:
                    healthy.append(server)
                    print(f"✅ {server} is healthy")
                else:
                    print(f"⚠️ {server} returned {r.status_code}")
            except Exception:
                print(f"❌ {server} is DOWN")
        HEALTHY_SERVERS = healthy
        time.sleep(5)

# Run health check in background
threading.Thread(target=check_health, daemon=True).start()


# --- Helper: Get next server (Round Robin) ---
def get_next_server():
    global CURRENT
    if not HEALTHY_SERVERS:
        return None
    server = HEALTHY_SERVERS[CURRENT % len(HEALTHY_SERVERS)]
    CURRENT = (CURRENT + 1) % len(HEALTHY_SERVERS)
    return server


# --- Main Reverse Proxy / Load Balancer Route ---
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def load_balance(path):
    if not HEALTHY_SERVERS:
        return jsonify({"error": "No healthy servers available"}), 503

    for _ in range(len(HEALTHY_SERVERS)):
        server = get_next_server()
        target_url = f"{server}/{path}"

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers if k.lower() != 'host'},
                data=request.get_data(),
                params=request.args,
                cookies=request.cookies,
                timeout=5
            )

            excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]

            return Response(resp.content, resp.status_code, headers)

        except Exception as e:
            print(f"⚠️ {server} failed: {e}")
            HEALTHY_SERVERS.remove(server)
            continue

    return jsonify({"error": "All backend servers failed"}), 503


# --- Load Balancer's Own Health Check ---
@app.route('/health')
def health():
    return jsonify({"status": "ok", "healthy_servers": HEALTHY_SERVERS})


if __name__ == '__main__':
    print("🚀 Load Balancer running on port 5000...")
    app.run(host='0.0.0.0', port=5000)
