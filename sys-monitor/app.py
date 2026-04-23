from flask import Flask, jsonify
import psutil

app = Flask(__name__)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "network_sent": psutil.net_io_counters().bytes_sent,
        "network_recv": psutil.net_io_counters().bytes_recv
    }
    return jsonify(stats)

if __name__ == '__main__':
    app.run(port=5000)
