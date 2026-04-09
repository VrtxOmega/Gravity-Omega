import os
import json
import sys

# Add the backend directory to the Python path to allow importing modules
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'security_scanner_modules')) # Add modules dir

from security_scanner_core import scan_file_content # Import core functions

def main():
    base_dir = "." # Corrected path
    findings = {
        'hardcoded_secrets': [], 'sensitive_files': [], 'exposed_bindings': [],
        'eval_exec_usage': [], 'missing_validation': [], 'errors': []
    }

    exclude_dirs = {'node_modules', '.git', 'dist', 'build', '__pycache__', '.venv', 'venv', '.next', 'out', 'coverage'}
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        if '.env' in files:
            findings['sensitive_files'].append({
                'file': os.path.join(root, '.env'), 'line': 1, 'severity': 'HIGH',
                'finding': ".env file detected.", 'context': "Contains environment variables, potentially secrets."
            })
        if 'config.json' in files:
            config_path = os.path.join(root, 'config.json')
            try:
                with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                    config_content = f.read()
                    if any(key in config_content for key in ['api_key', 'token', 'secret', 'password']):
                        findings['sensitive_files'].append({
                            'file': config_path, 'line': 1, 'severity': 'HIGH',
                            'finding': "config.json detected with potential credentials.",
                            'context': "Contains configuration, potentially secrets."
                        })
            except Exception as e:
                findings['errors'].append(f"Could not read {config_path}: {e}")

        for file in files:
            filepath = os.path.join(root, file)
            filename = os.path.basename(filepath)
            _, ext = os.path.splitext(filename)
            if ext.lower() in ['.py', '.js', '.env', '.json']:
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    scan_file_content(filepath, content, findings) # Pass findings directly
                except Exception as e:
                    findings['errors'].append(f"Could not read {filepath}: {e}")

    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0}
    for category in findings:
        if category != 'errors':
            for finding in findings[category]:
                severity_counts[finding['severity']] += 1

    output_data = {
        'total_findings_by_severity': severity_counts,
        'detailed_findings': findings
    }

    with open('security_findings.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4)

if __name__ == '__main__':
    main()
