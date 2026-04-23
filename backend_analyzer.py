import re
import json
import os
import ast

def analyze_backend_routes(filepath):
    routes = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.readlines()

    # Fixed regex: using (?:'|\x22) for quotes to avoid parser issues
    route_pattern = re.compile(r"@app\.route\((?:'|\x22)([^'\x22]+)(?:'|\x22),\s*(?:methods=\[([^\]]+)\])?\)")
    
    for i, line in enumerate(content):
        match = route_pattern.search(line)
        if match:
            url_pattern = match.group(1)
            methods_str = match.group(2)
            http_methods = []
            if methods_str:
                http_methods = [m.strip().strip("'\x22") for m in methods_str.split(',')] # Use hex escape for double quote
            else:
                http_methods = ['GET'] # Default to GET if not specified

            # Find the function definition following the route decorator
            func_name = None
            func_line_start = -1
            for j in range(i + 1, len(content)):
                func_match = re.search(r"def\s+(\w+)\s*\(", content[j])
                if func_match:
                    func_name = func_match.group(1)
                    func_line_start = j
                    break
            
            if func_name:
                has_error_handling = False
                has_auth_check = False
                
                # Scan function body for error handling and auth checks
                scan_start = func_line_start + 1
                scan_end = min(func_line_start + 20, len(content)) # Scan 20 lines after func def

                for k in range(scan_start, scan_end):
                    line_to_scan = content[k].lower()
                    # Check for try/except block. Simplified to check for 'try:' and 'except' in subsequent lines
                    if 'try:' in line_to_scan:
                        for l in range(k + 1, min(k + 5, scan_end)): # Check next few lines for 'except'
                            if 'except' in content[l].lower():
                                has_error_handling = True
                                break
                    if any(keyword in line_to_scan for keyword in ['token', 'auth', 'api_key', 'verify', 'hmac']):
                        has_auth_check = True
                
                routes.append({
                    'url_pattern': url_pattern,
                    'http_methods': http_methods,
                    'function_name': func_name,
                    'line_number': i + 1,
                    'has_error_handling': has_error_handling,
                    'has_auth_check': has_auth_check
                })
    return routes

if __name__ == '__main__':
    backend_file = r'C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py'
    output_file = r'C:\Veritas_Lab\gravity-omega-v2\api_routes_backend.json'
    
    # Create a dummy web_server.py if it doesn't exist for testing purposes
    if not os.path.exists(backend_file):
        os.makedirs(os.path.dirname(backend_file), exist_ok=True)
        with open(backend_file, 'w') as f:
            f.write('''
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        # Simulate some operation
        status = {'status': 'ok', 'version': '1.0'}
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data', methods=['POST'])
def post_data():
    # This route requires authentication
    token = request.headers.get('Authorization')
    if not token or not verify_token(token):
        return jsonify({'message': 'Unauthorized'}), 401
    try:
        data = request.json
        return jsonify({'received': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def verify_token(token):
    # Dummy token verification
    return token == 'valid_token_123'

@app.route('/api/info') # Defaults to GET
def get_info():
    # No explicit error handling or auth check
    return jsonify({'info': 'public data'})

@app.route('/api/admin', methods=['GET', 'POST'])
def admin_panel():
    # This route has an auth check but no explicit try/except
    api_key = request.args.get('api_key')
    if api_key != 'super_secret':
        return jsonify({'message': 'Forbidden'}), 403
    return jsonify({'admin_access': True})

@app.route('/api/dead_endpoint')
def dead_endpoint_route():
    return jsonify({'message': 'This endpoint is not called from frontend'})
''')

    routes_data = analyze_backend_routes(backend_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(routes_data, f, indent=4)
    print(f"Backend routes analysis saved to {output_file}")
