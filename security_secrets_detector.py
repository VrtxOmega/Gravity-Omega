import re

def redact_secret(value):
    if not isinstance(value, str) or len(value) < 4:
        return value
    return value[:4] + '***'

def detect_hardcoded_secrets(content, relative_path):
    findings = []
    secret_patterns = {
        r'(sk-[a-zA-Z0-9_]{16,})': 'API Key',
        r'(ghp_[a-zA-Z0-9_]{36,})': 'GitHub Token',
        r'(AIza[0-9A-Za-z-_]{35})': 'Google API Key',
        r'(Bearer [A-Za-z0-9-._~+/]{20,})': 'Bearer Token',
        r"(password|secret|api_key|token)\s*=\s*['\"]([^'\"]{5,})['\"]": 'Variable Assignment Secret'
    }
    for pattern_str, desc in secret_patterns.items():
        if 'Variable Assignment Secret' in desc:
            matches = re.finditer(pattern_str, content)
            for match in matches:
                full_line = content.splitlines()[content.count('\n', 0, match.start())]
                if not re.match(r'^\s*(#|import|from)', full_line):
                    secret_value = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    findings.append({
                        'severity': 'CRITICAL',
                        'category': 'Hardcoded Secrets',
                        'file': relative_path,
                        'finding': f'{desc}: {redact_secret(secret_value)}'
                    })
        else:
            matches = re.findall(pattern_str, content)
            for match in matches:
                findings.append({
                    'severity': 'CRITICAL',
                    'category': 'Hardcoded Secrets',
                    'file': relative_path,
                    'finding': f'{desc}: {redact_secret(match)}'
                })
    return findings
