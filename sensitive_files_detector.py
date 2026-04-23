import json
import os

def detect_sensitive_files(filepath, relative_path, content):
    findings = []
    if relative_path.endswith('.env'):
        findings.append({
            'severity': 'HIGH',
            'category': 'Sensitive File',
            'file': relative_path,
            'finding': '.env file detected, likely contains credentials.'
        })
    elif relative_path.endswith('config.json'):
        try:
            config_data = json.loads(content)
            if any(key in config_data for key in ['api_key', 'token', 'secret', 'password']):
                findings.append({
                    'severity': 'HIGH',
                    'category': 'Sensitive File',
                    'file': relative_path,
                    'finding': 'config.json contains potential credentials.'
                })
        except json.JSONDecodeError:
            pass
    return findings
