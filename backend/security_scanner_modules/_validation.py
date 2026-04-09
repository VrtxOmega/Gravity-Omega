import re

FLASK_ROUTE = re.compile(r'@app\.route\(|@blueprint\.route\(|@bp\.route\(')
DIRECT_ARGS = re.compile(r'request\.(args|form|json|data|values)\b')

def scan_missing_validation(filepath, line_num, line, prev_lines, ext, findings):
    if ext not in ('.py', '.js'):
        return
    
    stripped = line.strip()
    if stripped.startswith('#') or stripped.startswith('//'):
        return
    
    if DIRECT_ARGS.search(line):
        # Check if there's any validation in nearby context
        context_block = '\n'.join(prev_lines) + '\n' + line
        has_validation = any(kw in context_block for kw in [
            'validate', 'sanitize', 'escape', 'bleach', 'strip()',
            'isinstance(', 'int(', 'float(', '.get(', 'try:', 'except'
        ])
        if not has_validation:
            findings['missing_validation'].append({
                'file': filepath, 'line': line_num, 'severity': 'MEDIUM',
                'finding': "Request args used without visible validation.",
                'context': stripped[:120]
            })
