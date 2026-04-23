import re

def detect_eval_exec_usage(content, relative_path):
    findings = []
    if re.search(r'\beval\(', content) or re.search(r'\bexec\(', content):
        findings.append({
            'severity': 'MEDIUM',
            'category': 'Code Injection Risk',
            'file': relative_path,
            'finding': 'Usage of eval() or exec() detected.'
        })
    if re.search(r'subprocess\.run\([^)]*shell=True', content):
        findings.append({
            'severity': 'MEDIUM',
            'category': 'Code Injection Risk',
            'file': relative_path,
            'finding': 'subprocess.run with shell=True detected.'
        })
    return findings
