import re

EVAL_EXEC_PATTERN = re.compile(r'\b(eval|exec)\s*\(')
SHELL_TRUE_PATTERN = re.compile(r'shell\s*=\s*True')

def scan_eval_exec_usage(filepath, line_num, line, ext, findings):
    stripped = line.strip()
    # Skip comments
    if stripped.startswith('#') or stripped.startswith('//'):
        return
    
    match = EVAL_EXEC_PATTERN.search(line)
    if match:
        func_name = match.group(1)
        findings['eval_exec_usage'].append({
            'file': filepath, 'line': line_num, 'severity': 'HIGH',
            'finding': f"Dynamic code execution via {func_name}() detected.",
            'context': stripped[:120]
        })
    
    if SHELL_TRUE_PATTERN.search(line):
        findings['eval_exec_usage'].append({
            'file': filepath, 'line': line_num, 'severity': 'MEDIUM',
            'finding': "subprocess with shell=True (command injection risk).",
            'context': stripped[:120]
        })
