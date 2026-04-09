import ast
import re
import json

def analyze_routes(file_content):
    tree = ast.parse(file_content)
    routes_data = []
    critical_keywords = [
        'vault', 'provenance', 'requests', 'subprocess', 'exec', 'runSovereignModule',
        'download', 'upload', 'deleteFile', 'reboot', 'serviceCtrl', 'webSearch', 'fetchUrl',
        'writeFile', 'editFile', 'createDir', 'installPkg', 'generateImage'
    ]

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Check for Flask route decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ['route', 'get', 'post', 'put', 'delete']:
                        route_method = decorator.func.attr.upper() if decorator.func.attr != 'route' else 'ANY'
                        route_path = None
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                route_path = decorator.args[0].value
                            elif isinstance(decorator.args[0], ast.Call) and isinstance(decorator.args[0].func, ast.Attribute) and decorator.args[0].func.attr == 'json_route':
                                # Handle custom json_route decorator if it exists and takes a path
                                if decorator.args[0].args and isinstance(decorator.args[0].args[0], ast.Constant):
                                    route_path = decorator.args[0].args[0].value

                        if route_path:
                            function_name = node.name
                            line_number = node.lineno
                            
                            # Extract function body source
                            func_start = node.lineno - 1
                            func_end = node.end_lineno
                            func_lines = file_content.splitlines()[func_start:func_end]
                            func_body = "\n".join(func_lines)

                            # Check for try/except
                            has_error_handling = False
                            for sub_node in ast.walk(node):
                                if isinstance(sub_node, ast.Try):
                                    has_error_handling = True
                                    break
                            
                            # Check for criticality keywords
                            criticality_score = 0
                            for keyword in critical_keywords:
                                if re.search(r'\b' + re.escape(keyword) + r'\b', func_body, re.IGNORECASE):
                                    criticality_score += 1

                            routes_data.append({
                                'path': route_path,
                                'method': route_method,
                                'function_name': function_name,
                                'line_number': line_number,
                                'has_error_handling': has_error_handling,
                                'criticality_score': criticality_score,
                                'body': func_body # Include body for later inspection
                            })
    return routes_data

if __name__ == '__main__':
    file_path = r'C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    analyzed_routes = analyze_routes(content)
    
    # Filter for routes without error handling and sort by criticality
    vulnerable_routes = sorted(
        [r for r in analyzed_routes if not r['has_error_handling']],
        key=lambda x: x['criticality_score'],
        reverse=True
    )

    # Output the top 10 vulnerable routes
    output_path = r'C:\Users\rlope\.veritas\vulnerable_routes.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(vulnerable_routes[:10], f, indent=4)
    
    print(f"Analyzed routes and saved top 10 vulnerable to {output_path}")
