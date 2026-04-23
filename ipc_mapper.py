import re
import json

def scan_main_js_ipc_bridge(file_path):
    ipc_bridge_map = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except Exception as e:
        return {"error": f"Error reading file: {e}"}

    lines = content.splitlines()

    # Regex to find ipcMain.handle and capture channel name (more flexible)
    handle_declaration_pattern = re.compile(
        r"ipcMain\.handle\s*\(\s*['\\x22`](?P<channel_name>[^'\\x22`]+)['\\x22`]"
    )
    # Regex to find bridge.post/get calls
    bridge_call_pattern = re.compile(
        r"bridge\.(?:post|get)\s*\(\s*['\\x22`](?P<api_url>/api/[^'\\x22`]+)['\\x22`]"
    )

    current_channel = None
    in_handler_block = False
    brace_level = 0

    for i, line in enumerate(lines):
        if not in_handler_block:
            match_handle = handle_declaration_pattern.search(line)
            if match_handle:
                current_channel = match_handle.group('channel_name')
                for j in range(i, len(lines)):
                    sub_line = lines[j]
                    if '{' in sub_line:
                        in_handler_block = True
                        brace_level = 1 + sub_line.count('{') - sub_line.count('}')
                        break
                continue

        if in_handler_block:
            brace_level += line.count('{')
            brace_level -= line.count('}')

            if brace_level <= 0:
                in_handler_block = False
                current_channel = None
                continue

            if current_channel:
                match_bridge = bridge_call_pattern.search(line)
                if match_bridge:
                    api_url = match_bridge.group('api_url')
                    ipc_bridge_map[current_channel] = api_url

    return ipc_bridge_map
