import json
import re
import os
import traceback # Import traceback for use in the generated error response
from flask import current_app # Import current_app for logging

def inject_error_handling(routes_data, original_file_content):
    modified_content = original_file_content
    
    # 1. Handle imports (traceback and jsonify)
    if 'import traceback' not in modified_content:
        modified_content = modified_content.replace('import json', 'import json\nimport traceback')
    
    # Check if jsonify is already imported from flask
    if 'from flask import jsonify' not in modified_content and 'jsonify' not in re.search(r'from flask import (.*)', modified_content).group(1):
        # Check if 'from flask import request' exists and add jsonify to it
        match = re.search(r'(from flask import\s*)([^\n]*)', modified_content)
        if match:
            existing_imports = match.group(2).strip()
            if 'jsonify' not in existing_imports:
                new_imports = f"{match.group(1)}{existing_imports}, jsonify"
                modified_content = modified_content.replace(match.group(0), new_imports)
        else:
            # Fallback if 'from flask import request' is not found, add a new line
            modified_content = modified_content.replace('import json', 'import json\nfrom flask import jsonify')


    # 2. Wrap routes with try/except
    for route in routes_data:
        func_body = route['body']
        function_name = route['function_name']
        
        # Ensure we only process routes that truly don't have try/except
        if 'try:' in func_body and 'except Exception as e:' in func_body:
            print(f"Skipping {function_name} as it appears to already have error handling.")
            continue

        # Find the function definition line
        func_def_match = re.search(r'def ' + re.escape(function_name) + r'\([^)]*\):', func_body)
        if not func_def_match:
            continue

        # Extract the indentation of the function definition line
        def_line_indent_match = re.match(r'^(\s*)def', func_body)
        def_line_indent = def_line_indent_match.group(1) if def_line_indent_match else ''

        # Split the function body into lines
        lines = func_body.splitlines()
        
        # The first line is 'def function_name():'
        def_line = lines[0]
        
        # The actual content to wrap (all lines after 'def' line)
        content_to_wrap_raw = "\n".join(lines[1:])
        
        # Determine the base indentation of the function's actual body (usually 4 spaces more than 'def')
        # We need to find the smallest common indentation of the actual body lines
        body_lines_stripped = [line for line in content_to_wrap_raw.splitlines() if line.strip()]
        if not body_lines_stripped: # Empty function body
            continue

        # Find the indentation of the first non-empty line after the def
        first_body_line_indent_match = re.match(r'^(\s*)', body_lines_stripped[0])
        base_body_indent = first_body_line_indent_match.group(1) if first_body_line_indent_match else def_line_indent + '    '

        # Re-indent the content to be wrapped inside the try block
        # Each line of the original body needs to be indented by an additional 4 spaces
        wrapped_content_indented = "\n".join([base_body_indent + '    ' + line[len(base_body_indent):] if line.strip() else line for line in content_to_wrap_raw.splitlines()])
        
        # Construct the new function body with try/except
        new_func_body = f"""{def_line}
{base_body_indent}try:
{wrapped_content_indented}
{base_body_indent}except Exception as e:
{base_body_indent}    current_app.logger.error(f"Error in {function_name}: {{e}}", exc_info=True)
{base_body_indent}    return jsonify({{'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}}), 500"""

        # Replace the original function body with the new one in the modified_content
        # Use re.escape for the find string to handle special characters in the original body
        # This is the tricky part: we need to replace the *exact* original function body string
        # with the new one.
        modified_content = modified_content.replace(func_body, new_func_body)
    
    return modified_content

if __name__ == '__main__':
    routes_file = r'C:\Users\rlope\.veritas\vulnerable_routes.json'
    web_server_path = r'C:\Veritas_Lab\gravity-omega-v2\backend\web_server.py'

    with open(routes_file, 'r', encoding='utf-8') as f:
        vulnerable_routes = json.load(f)
    
    with open(web_server_path, 'r', encoding='utf-8') as f:
        web_server_content = f.read()

    final_modified_content = inject_error_handling(vulnerable_routes, web_server_content)

    # Directly write the modified content back to web_server.py
    with open(web_server_path, 'w', encoding='utf-8') as f:
        f.write(final_modified_content)
    
    print(f"Successfully injected error handling into {web_server_path}")
