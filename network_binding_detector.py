import re

def detect_exposed_network_bindings(content, relative_path):
    findings = []
    pat1 = r"host=['\x22]0\.0\.0\.0['\x22]"
    pat2 = r"\.listen\(\s*\d+,\s*['\x22]0\.0\.0\.0['\x22]\)"
    if re.search(pat1, content) or re.search(pat2, content):
        findings.append({
            'severity': 'MEDIUM',
            'category': 'Exposed Network Binding',
            'file': relative_path,
            'finding': 'Network binding to 0.0.0.0 detected.'
        })
    return findings
