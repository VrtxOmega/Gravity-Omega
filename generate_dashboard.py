import json
import os
import subprocess

def generate_html_dashboard(project_root):
    results_path = os.path.join(project_root, 'security_scan_results.json')
    template_path = os.path.join(project_root, 'dashboard_template.html')
    output_path = os.path.join(project_root, 'security_dashboard.html')

    if not os.path.exists(results_path):
        print(f"Error: Scan results file not found at {results_path}. Please run security_scanner.py first.")
        return
    if not os.path.exists(template_path):
        print(f"Error: Dashboard template file not found at {template_path}.")
        return

    with open(results_path, 'r', encoding='utf-8') as f:
        scan_data = json.load(f)

    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # Populate summary counts
    html_output = html_template.replace('{{CRITICAL_COUNT}}', str(scan_data['severity_counts'].get('CRITICAL', 0)))
    html_output = html_output.replace('{{HIGH_COUNT}}', str(scan_data['severity_counts'].get('HIGH', 0)))
    html_output = html_output.replace('{{MEDIUM_COUNT}}', str(scan_data['severity_counts'].get('MEDIUM', 0)))

    # Populate detailed findings
    detailed_findings_html = []
    for category, findings in scan_data['findings_by_category'].items():
        detailed_findings_html.append(f"<div class='category-group'>") # Fixed quoting here
        detailed_findings_html.append(f"<h3>{category}</h3>")
        if not findings:
            detailed_findings_html.append(f"<p class='no-findings'>No findings in this category.</p>") # Fixed quoting here
        else:
            for finding in findings:
                severity_class = finding['severity']
                detailed_findings_html.append(f"<div class='finding-item {severity_class}'>") # Fixed quoting here
                detailed_findings_html.append(f"<p><strong>File:</strong> {finding['file']}</p>")
                detailed_findings_html.append(f"<p><strong>Finding:</strong> {finding['finding']}</p>")
                detailed_findings_html.append(f"</div>")
        detailed_findings_html.append(f"</div>")

    html_output = html_output.replace('{{DETAILED_FINDINGS}}', '\n'.join(detailed_findings_html))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"Dashboard generated: {output_path}")

    # Open the dashboard in the browser
    try:
        subprocess.run(['powershell', '-Command', f'Start-Process "{output_path}"'], check=True)
        print(f"Opened dashboard in browser.")
    except subprocess.CalledProcessError as e:
        print(f"Error opening browser: {e}")
    except FileNotFoundError:
        print("Error: PowerShell not found. Cannot open browser automatically.")


if __name__ == "__main__":
    project_root = "C:\\Veritas_Lab\\gravity-omega-v2"
    # First, run the scanner to ensure results are fresh
    print("Running security scanner...")
    try:
        subprocess.run(['python', os.path.join(project_root, 'security_scanner.py')], check=True, cwd=project_root)
        print("Security scanner finished.")
        generate_html_dashboard(project_root)
    except subprocess.CalledProcessError as e:
        print(f"Error running security scanner: {e}")
    except FileNotFoundError:
        print("Error: Python not found or security_scanner.py script missing.")
