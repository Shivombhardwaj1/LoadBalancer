from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"server": "Server 1", "message": "Hello from Server 1"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(port=5003)
