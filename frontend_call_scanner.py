import os
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

    # Regex to find ipcMain.handle and capture channel name
    handle_start_pattern = re.compile(
        r"ipcMain\.handle\s*\(\s*['\\x22`](?P<channel_name>[^'\\x22`]+)['\\x22`]\s*,\s*async\s*\(event,\s*(?:[^)]*?)\)\s*=>\s*{"
    )
    # Regex to find bridge.post/get calls
    bridge_call_pattern = re.compile(
        r"bridge\.(?:post|get)\s*\(\s*['\\x22`](?P<api_url>/api/[^'\\x22`]+)['\\x22`]"
    )

    current_channel = None
    in_handler_block = False
    brace_level = 0

    for i, line in enumerate(lines):
        # Check for start of ipcMain.handle
        match_handle = handle_start_pattern.search(line)
        if match_handle:
            current_channel = match_handle.group('channel_name')
            in_handler_block = True
            brace_level = 1 # We just opened the first brace for the handler
            continue

        if in_handler_block:
            # Track brace level to find end of handler block
            brace_level += line.count('{')
            brace_level -= line.count('}')

            if brace_level <= 0: # End of handler block
                in_handler_block = False
                current_channel = None
                continue

            # Look for bridge calls within the handler block
            if current_channel:
                match_bridge = bridge_call_pattern.search(line)
                if match_bridge:
                    api_url = match_bridge.group('api_url')
                    ipc_bridge_map[current_channel] = api_url
                    # Assuming one API call per handler for simplicity, or first one found.
                    # If multiple, this will just take the last one.

    return ipc_bridge_map

def scan_frontend_calls_with_map(base_dirs, ipc_bridge_map):
    frontend_calls = []
    # Regex for window.omega.X() or ipcRenderer.invoke('channel:name')
    # This pattern captures the 'X' in window.omega.X() or the 'channel:name' in invoke
    call_pattern = re.compile(
        r"(?:window\.omega\.(?P<omega_func>[a-zA-Z0-9_]+)|ipcRenderer\.invoke\s*\(\s*['\\x22`](?P<ipc_channel>[^'\\x22`]+)['\\x22`])"
    )

    for base_dir in base_dirs:
        for root, _, files in os.walk(base_dir):
            # Exclude common build/dependency directories
            if 'node_modules' in root or '.git' in root or 'dist' in root or 'build' in root or '__pycache__' in root or 'venv' in root or '.venv' in root:
                continue

            for file in files:
                if file.endswith('.js'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for match in call_pattern.finditer(content):
                                omega_func = match.group('omega_func')
                                ipc_channel = match.group('ipc_channel')

                                if omega_func: # It's a window.omega.X() call
                                    # window.omega.X() maps directly to an IPC channel named 'omega:X'
                                    resolved_channel = f"omega:{omega_func}"
                                elif ipc_channel: # It's an ipcRenderer.invoke('channel:name') call
                                    resolved_channel = ipc_channel
                                else:
                                    continue # Should not happen

                                # Resolve the channel to an API URL using the map
                                api_url = ipc_bridge_map.get(resolved_channel)
                                if api_url:
                                    frontend_calls.append({"file": file_path, "resolved_url": api_url, "original_call": match.group(0)})
                                else:
                                    # If a channel is invoked but not mapped to an API, it might be an internal IPC or a dead channel
                                    frontend_calls.append({"file": file_path, "resolved_url": f"UNMAPPED_CHANNEL:{resolved_channel}", "original_call": match.group(0)})

                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
    return frontend_calls

if __name__ == "__main__":
    main_js_file = r"C:\\Veritas_Lab\\gravity-omega-v2\\main.js"
    renderer_dir = r"C:\\Veritas_Lab\\gravity-omega-v2\\renderer"
    omega_dir = r"C:\\Veritas_Lab\\gravity-omega-v2\\omega"
    
    ipc_map_output_file = r"C:\\Veritas_Lab\\gravity-omega-v2\\ipc_bridge_map.json"
    frontend_calls_output_file = r"C:\\Veritas_Lab\\gravity-omega-v2\\frontend_calls.json"

    # Pass 1: Scan main.js to build the IPC bridge map
    ipc_map = scan_main_js_ipc_bridge(main_js_file)
    with open(ipc_map_output_file, 'w', encoding='utf-8') as f:
        json.dump(ipc_map, f, indent=2)
    print(f"IPC bridge map saved to {ipc_map_output_file}")
    print(f"Total IPC channels mapped: {len(ipc_map)}\
")

    # Pass 2: Scan renderer and omega directories using the map
    all_frontend_calls = scan_frontend_calls_with_map([renderer_dir, omega_dir], ipc_map)

    with open(frontend_calls_output_file, 'w', encoding='utf-8') as f:
        json.dump(all_frontend_calls, f, indent=2)
    print(f"Frontend API calls saved to {frontend_calls_output_file}")
    print(f"Total frontend calls found: {len(all_frontend_calls)}")