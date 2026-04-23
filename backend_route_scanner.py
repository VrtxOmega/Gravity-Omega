import re
import os
import json
import ast

def analyze_flask_routes(file_path):
    routes_data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find @app.route decorators and their associated function
    # This regex captures the route path and optionally the methods, then the function definition
    route_pattern = re.compile(r"@app\.route\((?P<route_args>[^)]+)\)\s*(?:@\w+\.\w+\([^)]+\)\s*)*def\s+(?P<func_name>\w+)\s*\((?P<func_args>[^)]*)\):")
    
    # Find all route matches
    matches = list(route_pattern.finditer(content))

    lines = content.splitlines()

    for match in matches:
        route_args = match.group('route_args')
        func_name = match.group('func_name')
        start_line = content.count('\n', 0, match.start()) + 1 # Line number of @app.route

        url_pattern = ''
        methods = ['GET'] # Default method if not specified

        # Extract URL pattern - corrected regex using \x22 for double quotes
        url_match = re.search(r"(?:'|\x22)(?P<url>[^'\x22]+)(?:'|\x22)", route_args)
        if url_match:
            url_pattern = url_match.group('url')

        # Extract HTTP methods
        methods_match = re.search(r"methods\s*=\s*\[(?P<methods>[^\]]+)\]", route_args)
        if methods_match:
            methods_str = methods_match.group('methods')
            methods = [m.strip().strip(r"'\x22") for m in methods_str.split(',')] # Handle single/double quotes

        # Find the function body
        func_start_index = match.end()
        func_end_index = -1
        
        # Use AST to find the exact function body for robust parsing
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    # Check if this function definition is the one associated with the current route match
                    # by comparing line numbers. The decorator is on the line before the 'def'
                    if node.lineno == start_line + 1: # 'def' line is usually 1 after '@app.route'
                        func_body_start_line = node.lineno
                        # Find the end line of the function
                        func_body_end_line = node.body[-1].lineno if node.body else node.lineno
                        # Adjust for multi-line statements
                        if node.body and hasattr(node.body[-1], 'end_lineno'):
                            func_body_end_line = node.body[-1].end_lineno
                        
                        func_body_lines = lines[func_body_start_line - 1 : func_body_end_line]
                        func_body_text = '\n'.join(func_body_lines)
                        
                        has_error_handling = bool(re.search(r"try\s*:", func_body_text) and re.search(r"except\s*:", func_body_text))
                        has_auth_check = bool(re.search(r"(token|auth|api_key|verify|hmac)", func_body_text, re.IGNORECASE))
                        
                        routes_data.append({
                            'url_pattern': url_pattern,
                            'http_methods': methods,
                            'function_name': func_name,
                            'line_number': start_line,
                            'has_error_handling': has_error_handling,
                            'has_auth_check': has_auth_check
                        })
                        break # Found the correct function, move to next route
        except SyntaxError as e:
            print(f"Syntax error parsing file: {e}")
            # Fallback to simpler line-based search if AST fails
            # This is less robust but better than nothing
            func_body_start_line = start_line + 1
            indent = len(lines[func_body_start_line - 1]) - len(lines[func_body_start_line - 1].lstrip())
            func_body_end_line = func_body_start_line
            for i in range(func_body_start_line, len(lines)):
                if not lines[i].strip(): # Empty line
                    continue
                current_indent = len(lines[i]) - len(lines[i].lstrip())
                if current_indent <= indent and lines[i].strip(): # End of function block
                    break
                func_body_end_line = i + 1
            
            func_body_text = '\n'.join(lines[func_body_start_line - 1 : func_body_end_line])
            has_error_handling = bool(re.search(r"try\s*:", func_body_text) and re.search(r"except\s*:", func_body_text))
            has_auth_check = bool(re.search(r"(token|auth|api_key|verify|hmac)", func_body_text, re.IGNORECASE))
            
            routes_data.append({
                'url_pattern': url_pattern,
                'http_methods': methods,
                'function_name': func_name,
                'line_number': start_line,
                'has_error_handling': has_error_handling,
                'has_auth_check': has_auth_check
            })


    return routes_data

if __name__ == '__main__':
    backend_file = r'C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py'
    output_file = r'C:\Veritas_Lab\gravity-omega-v2\backend_routes.json'
    
    if os.path.exists(backend_file):
        routes = analyze_flask_routes(backend_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=4)
        print(f"Backend route analysis complete. Data saved to {output_file}")
    else:
        print(f"Error: Backend file not found at {backend_file}")
