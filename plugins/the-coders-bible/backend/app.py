"""
The Coder's Bible — Flask API Server
Port: 5090
Serves the Bible search API + static frontend.
"""

import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))
from bible_engine import BibleEngine

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'),
    static_url_path=''
)
CORS(app)

engine = BibleEngine()


# ─── Static Frontend ────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# ─── API: Analyze Snippet ───────────────────────────────────
@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Full analysis of a code snippet."""
    data = request.get_json()
    if not data or 'snippet' not in data:
        return jsonify({"error": "Missing 'snippet' field"}), 400

    snippet = data['snippet']
    if len(snippet) > 10000:
        return jsonify({"error": "Snippet too large (max 10,000 chars)"}), 400

    result = engine.analyze(snippet)
    return jsonify(result)


# ─── API: Search ─────────────────────────────────────────────
@app.route('/api/search', methods=['GET'])
def search():
    """Direct FTS5 search."""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)

    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    results = engine.search(query, limit=limit)
    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    })


# ─── API: Stats ──────────────────────────────────────────────
@app.route('/api/stats')
def stats():
    """Database statistics."""
    return jsonify(engine.get_stats())


# ─── API: Health ─────────────────────────────────────────────
@app.route('/api/health')
def health():
    """Health check."""
    try:
        count = engine._get_total_count()
        return jsonify({
            "status": "ok",
            "engine": "bible_engine",
            "fragments": count,
            "db_path": engine.db_path
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─── Main ────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('BIBLE_PORT', 5090))
    print(f"+----------------------------------------------+")
    print(f"|  CODER'S BIBLE -- Knowledge Engine v1.0      |")
    print(f"|  Port: {port}                                 |")
    print(f"|  DB: {engine.db_path[:38]:<38} |")
    print(f"+----------------------------------------------+")
    app.run(host='127.0.0.1', port=port, debug=True)
