import re
import json
import os

def analyze_frontend_calls(directories):
    frontend_calls = []
    # Fixed regex: using (?:'|\x22|`) for quotes to avoid parser issues
    fetch_pattern = re.compile(r"fetch\((?:'|\x22|`)\s*(https?://[^'\x22`]+)(?:'|\x22|`)\)")
    axios_pattern = re.compile(r"axios\.(?:get|post|put|delete|patch)\((?:'|\x22|`)\s*(https?://[^'\x22`]+)(?:'|\x22|`)\)")

    for base_dir in directories:
        for root, dirs, files in os.walk(base_dir):
            # Exclude common build/dependency directories
            dirs[:] = [d for d in dirs if d not in {'node_modules', '.git', 'dist', 'build', '__pycache__', 'venv', '.venv'}]
            for file in files:
                if file.endswith('.js'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            for match in fetch_pattern.finditer(content):
                                frontend_calls.append({'url': match.group(1), 'source_file': filepath})
                            
                            for match in axios_pattern.finditer(content):
                                frontend_calls.append({'url': match.group(1), 'source_file': filepath})
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")
    return frontend_calls

if __name__ == '__main__':
    frontend_dirs = [
        r'C:\Veritas_Lab\gravity-omega-v2\renderer',
        r'C:\Veritas_Lab\gravity-omega-v2\omega'
    ]
    output_file = r'C:\Veritas_Lab\gravity-omega-v2\api_calls_frontend.json'

    # Create dummy JS files for testing if directories don't exist
    for d in frontend_dirs:
        os.makedirs(d, exist_ok=True)
    
    dummy_renderer_file = r'C:\Veritas_Lab\gravity-omega-v2\renderer\app.js'
    if not os.path.exists(dummy_renderer_file):
        with open(dummy_renderer_file, 'w') as f:
            f.write('''
console.log("Renderer app loaded");
fetch('/api/status').then(res => res.json()).then(data => console.log(data));
axios.post('/api/data', {id: 1}).then(res => console.log(res.data));
fetch('https://external.api/metrics').then(res => res.json());
''')

    dummy_omega_file = r'C:\Veritas_Lab\gravity-omega-v2\omega\omega_agent.js'
    if not os.path.exists(dummy_omega_file):
        with open(dummy_omega_file, 'w') as f:
            f.write('''
console.log("Omega agent running");
fetch('/api/info').then(res => res.json()).then(data => console.log(data));
axios.get('/api/admin?api_key=super_secret').then(res => console.log(res.data));
fetch('http://localhost:5000/api/internal/health').then(res => res.json());
fetch('http://localhost:5000/api/non_existent_route').then(res => res.json()); // Orphan call
''')

    calls_data = analyze_frontend_calls(frontend_dirs)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(calls_data, f, indent=4)
    print(f"Frontend calls analysis saved to {output_file}")
