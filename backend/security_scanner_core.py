import os
from security_scanner_modules._secrets import scan_hardcoded_secrets
from security_scanner_modules._bindings import scan_exposed_bindings
from security_scanner_modules._eval_exec import scan_eval_exec_usage
from security_scanner_modules._validation import scan_missing_validation

def scan_file_content(filepath, content, findings):
    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    lines = content.splitlines()
    for i, line in enumerate(lines):
        line_num = i + 1
        prev_lines = lines[max(0, i-5):i]

        scan_hardcoded_secrets(filepath, line_num, line, findings)
        scan_exposed_bindings(filepath, line_num, line, findings)
        scan_eval_exec_usage(filepath, line_num, line, ext, findings)
        scan_missing_validation(filepath, line_num, line, prev_lines, ext, findings)
