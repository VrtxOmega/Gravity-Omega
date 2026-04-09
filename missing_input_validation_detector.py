import re

def detect_missing_input_validation(content, relative_path):
    findings = []
    quote_char = "['\x22]"
    # For Flask (Python)
    if relative_path.endswith('.py') and ('flask' in content.lower() or 'request' in content):
        flask_pat = r"request\.(args|form|json|data)\.get\(" + quote_char + r"\w+" + quote_char + r"\)"
        sanitize_pat = r"(validate|sanitize|escape)\("
        if re.search(flask_pat, content) and not re.search(sanitize_pat, content):
            findings.append({
                'severity': 'MEDIUM',
                'category': 'Missing Input Validation',
                'file': relative_path,
                'finding': 'Potential direct use of Flask request data without explicit validation/sanitization.'
            })
    # For Express (Node.js)
    if relative_path.endswith('.js') and ('express' in content or 'req.' in content):
        express_pat = r"req\.(query|params|body)\.\w+"
        sanitize_pat = r"(validate|sanitize|escape)\("
        if re.search(express_pat, content) and not re.search(sanitize_pat, content):
            findings.append({
                'severity': 'MEDIUM',
                'category': 'Missing Input Validation',
                'file': relative_path,
                'finding': 'Potential direct use of Express request data without explicit validation/sanitization.'
            })
    return findings
