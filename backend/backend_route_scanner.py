import re
import os
import json

def scan_backend_routes(file_path):
    routes = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except Exception as e:
        return {"error": f"Error reading file: {e}"}

    lines = content.splitlines()
    
    # Regex to find @app.route decorators
    route_decorator_pattern = re.compile(
        r"@app\.route\s*\(\s*(r?['\x22])(?P<url>.*?)\1\s*(?:,\s*methods=\[(?P<methods>.*?)\])?\s*\)"
    )
    
    # Regex to find function definitions
    function_def_pattern = re.compile(r"def\s+(?P<function_name>[a-zA-Z0-9_]+)\s*\(")
    
    # Keywords for authentication check
    auth_keywords = ['token', 'auth', 'api_key', 'verify', 'hmac', 'login_required']
    
    # Iterate through lines to find routes and their associated functions
    i = 0
    while i < len(lines):
        line = lines[i]
        match_route = route_decorator_pattern.search(line)
        
        if match_route:
            url = match_route.group('url')
            methods_str = match_route.group('methods')
            methods = [m.strip().strip("'\x22") for m in methods_str.split(',')] if methods_str else ['GET'] # Default to GET if not specified
            
            route_info = {
                "url": url,
                "methods": methods,
                "function_name": "UNKNOWN",
                "line_number": i + 1,
                "has_error_handling": False,
                "has_auth_check": False
            }
            
            # Look for the function definition and other details in subsequent lines
            j = i + 1
            auth_decorator_found = False
            while j < len(lines) and j < i + 20: # Look within 20 lines for function def
                sub_line = lines[j].strip()
                
                if "@login_required" in sub_line:
                    auth_decorator_found = True
                
                match_func = function_def_pattern.match(sub_line)
                if match_func:
                    route_info["function_name"] = match_func.group('function_name')
                    
                    # Scan function body for error handling and auth checks
                    k = j + 1
                    func_body_lines = []
                    indent_level = len(lines[j]) - len(lines[j].lstrip()) # Indent of the def line
                    
                    while k < len(lines):
                        body_line = lines[k]
                        current_indent = len(body_line) - len(body_line.lstrip())
                        if not body_line.strip() or current_indent > indent_level: # Continue if blank or more indented
                            func_body_lines.append(body_line)
                        elif current_indent <= indent_level and body_line.strip(): # End of function body
                            break
                        k += 1
                    
                    func_body = "\
".join(func_body_lines)
                    
                    if "try:" in func_body and "except" in func_body:
                        route_info["has_error_handling"] = True
                    
                    if auth_decorator_found or any(keyword in func_body for keyword in auth_keywords):
                        route_info["has_auth_check"] = True
                    
                    break # Found function definition, stop looking
                j += 1
            routes.append(route_info)
        i += 1
    
    return routes

if __name__ == "__main__":
    backend_file = r"C:\\Veritas_Lab\\gravity-omega-v2\\backend\\web_server.py"
    output_file = r"C:\\Veritas_Lab\\gravity-omega-v2\\backend\\backend_routes.json"
    all_routes = scan_backend_routes(backend_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_routes, f, indent=2)
    print(f"Backend routes saved to {output_file}")
    print(f"Total routes found: {len(all_routes)}")