import re

def redact_secret(value):
    if len(value) > 4:
        return value[:4] + '***'
    return '***'

SECRET_VAR_ASSIGNMENT_SINGLE_QUOTE = re.compile(r"(?i)(password|secret|api_key|token)\s*=\s*'([^']+)'")
SECRET_VAR_ASSIGNMENT_DOUBLE_QUOTE = re.compile(r"(?i)(password|secret|api_key|token)\s*=\s*\"([^\"]+)\"")

def scan_hardcoded_secrets(filepath, line_num, line, findings):
    secret_patterns = {
        'CRITICAL': [
            re.compile(r'(sk-[a-zA-Z0-9_]{16,})'), re.compile(r'(ghp_[a-zA-Z0-9_]{36})'),
            re.compile(r'(AIza[0-9A-Za-z-_]{35})'), re.compile(r'(Bearer [A-Za-z0-9\\-\\._~+/]{30,})'),
        ],
        'HIGH': [SECRET_VAR_ASSIGNMENT_SINGLE_QUOTE, SECRET_VAR_ASSIGNMENT_DOUBLE_QUOTE]
    }
    for severity, patterns in secret_patterns.items():
        for pattern_re in patterns:
            if (pattern_re == SECRET_VAR_ASSIGNMENT_SINGLE_QUOTE or pattern_re == SECRET_VAR_ASSIGNMENT_DOUBLE_QUOTE) and \
               (line.strip().startswith('#') or line.strip().startswith('import') or line.strip().startswith('from')):
                continue
            match = pattern_re.search(line)
            if match:
                secret_value = match.group(1) if len(match.groups()) == 1 else match.group(2)
                if secret_value:
                    findings['hardcoded_secrets'].append({
                        'file': filepath, 'line': line_num, 'severity': severity,
                        'finding': f"Hardcoded secret detected: {redact_secret(secret_value)}",
                        'context': line.strip()
                    })
