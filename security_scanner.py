import os
import json
from security_secrets_detector import detect_hardcoded_secrets
from sensitive_files_detector import detect_sensitive_files
from network_binding_detector import detect_exposed_network_bindings
from eval_exec_detector import detect_eval_exec_usage
from missing_input_validation_detector import detect_missing_input_validation

def scan_file_for_security_issues(filepath, project_root):
    findings = []
    relative_path = os.path.relpath(filepath, project_root)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return [{'severity': 'MEDIUM', 'category': 'File Access Error', 'file': relative_path, 'finding': f'Could not read file: {e}'}]

    findings.extend(detect_hardcoded_secrets(content, relative_path))
    findings.extend(detect_sensitive_files(filepath, relative_path, content))
    findings.extend(detect_exposed_network_bindings(content, relative_path))
    findings.extend(detect_eval_exec_usage(content, relative_path))
    findings.extend(detect_missing_input_validation(content, relative_path))

    return findings

def main():
    project_root = r"C:\Veritas_Lab\gravity-omega-v2"
    all_findings = []
    excluded_dirs = {'node_modules', '.git', 'dist', 'build', '__pycache__', '.venv', 'venv', '.next', 'out', 'coverage'}
    allowed_extensions = ('.py', '.js', '.env', '.json')

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in excluded_dirs] # Prune directories
        for file in files:
            if file.endswith(allowed_extensions) and not file.endswith('.min.js'):
                filepath = os.path.join(root, file)
                all_findings.extend(scan_file_for_security_issues(filepath, project_root))

    # Aggregate findings by severity
    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0}
    for finding in all_findings:
        severity_counts[finding['severity']] += 1

    # Prepare data for HTML
    findings_by_category = {}
    for finding in all_findings:
        category = finding['category']
        if category not in findings_by_category:
            findings_by_category[category] = []
        findings_by_category[category].append(finding)

    # Save findings to a JSON file for the HTML generator
    output_data = {
        'severity_counts': severity_counts,
        'findings_by_category': findings_by_category
    }
    output_path = os.path.join(project_root, 'security_scan_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4)

    print(f"Scan complete. Results saved to {output_path}")

if __name__ == "__main__":
    main()
