def scan_exposed_bindings(filepath, line_num, line, findings):
    if "host='0.0.0.0'" in line or 'host="0.0.0.0"' in line:
        findings['exposed_bindings'].append({
            'file': filepath, 'line': line_num, 'severity': 'CRITICAL',
            'finding': "Exposed network binding (0.0.0.0) detected.",
            'context': line.strip()
        })
