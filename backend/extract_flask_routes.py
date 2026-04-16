import os
import re
import json

def extract_flask_routes(file_path):
    routes = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

    # Robust regex to capture @app.route('/path', methods=[...])
    # Group 1: URL pattern
    # Group 2: Content inside methods=[...] (e.g., "'GET', 'POST'")
    route_decorator_pattern = re.compile(r"@app\\.route\\((?:'|\")([^'\"]+?)(?:'|\")(?:,\\s*methods=\\\[(.*?)\\\])?)")
    function_def_pattern = re.compile(r"def\\s+(\\w+)\\s*\\(")
    method_name_pattern = re.compile(r"(?:'|\")(\\w+)(?:'|\")") # To extract individual method names

    for i, line in enumerate(content):
        match = route_decorator_pattern.search(line)
        if match:
            url_pattern = match.group(1)
            methods_inner_content = match.group(2) # This will be "'GET', 'POST'" or None
            http_methods = ['GET'] # Default to GET if not specified

            if methods_inner_content:
                extracted_methods = method_name_pattern.findall(methods_inner_content)
                if extracted_methods:
                    http_methods = [m.upper() for m in extracted_methods]

            # Find the function definition immediately following the route decorator
            func_name = None
            func_start_line = -1
            for j in range(i + 1, min(i + 10, len(content))): # Look within next 10 lines for function def
                func_match = function_def_pattern.search(content[j])
                if func_match:
                    func_name = func_match.group(1)
                    func_start_line = j
                    break

            if func_name:
                # Extract function body for analysis (up to next route or function def, or end of file)
                func_body_lines = []
                # Look for function body within a reasonable range (e.g., 100 lines)
                for k in range(func_start_line + 1, min(func_start_line + 100, len(content))):
                    if route_decorator_pattern.search(content[k]) or function_def_pattern.search(content[k]):
                        break
                    func_body_lines.append(content[k].strip())
                func_body = "\\n".join(func_body_lines)

                # Check for error handling (try/except) within 20 lines of function start
                has_error_handling = False
                for l in range(func_start_line, min(func_start_line + 20, len(content))):
                    if 'try:' in content[l]:
                        has_error_handling = True
                        break

                # Check for authentication keywords
                auth_keywords = ['token', 'auth', 'api_key', 'verify', 'hmac', 'jwt', 'session', 'authenticate']
                has_auth_check = any(keyword in func_body for keyword in auth_keywords)

                routes.append({
                    'url_pattern': url_pattern,
                    'http_methods': http_methods,
                    'function_name': func_name,
                    'line_number': i + 1, # 1-based line number
                    'has_error_handling': has_error_handling,
                    'has_auth_check': has_auth_check
                })
    return routes

if __name__ == '__main__':
    backend_dir = r'backend'
    web_server_path = os.path.join(backend_dir, 'web_server.py')
    output_json_path = os.path.join(backend_dir, 'backend_routes.json')

    flask_routes = extract_flask_routes(web_server_path)
    if flask_routes:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(flask_routes, f, indent=4)
        print(f"Extracted {len(flask_routes)} Flask routes to {output_json_path}")
    else:
        print(f"No Flask routes extracted or an error occurred.")
