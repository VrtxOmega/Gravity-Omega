import json
import os

def generate_dashboard():
    try:
        with open('security_findings.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: security_findings.json not found. Run security_scanner_main.py first.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode security_findings.json. Check file integrity.")
        return

    template_path = 'C:\\Veritas_Lab\\gravity-omega-v2\\backend\\security_dashboard_template.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    total_critical = data['total_findings_by_severity'].get('CRITICAL', 0)
    total_high = data['total_findings_by_severity'].get('HIGH', 0)
    total_medium = data['total_findings_by_severity'].get('MEDIUM', 0)

    def format_findings(findings_list):
        if not findings_list:
            return '<p class="no-findings">No findings in this category.</p>'
        
        html_output = []
        for finding in findings_list:
            html_output.append(f'''
            <div class="finding-item {finding['severity']}">
                <p><strong>Severity:</strong> {finding['severity']}</p>
                <p><strong>File:</strong> {finding['file']}</p>
                <p><strong>Line:</strong> {finding['line']}</p>
                <p><strong>Finding:</strong> {finding['finding']}</p>
                <p><strong>Context:</strong> <span class="context">{finding['context']}</span></p>
            </div>
            ''')
        return '\
'.join(html_output)

    hardcoded_secrets_html = format_findings(data['detailed_findings']['hardcoded_secrets'])
    sensitive_files_html = format_findings(data['detailed_findings']['sensitive_files'])
    exposed_bindings_html = format_findings(data['detailed_findings']['exposed_bindings'])
    eval_exec_usage_html = format_findings(data['detailed_findings']['eval_exec_usage'])
    missing_validation_html = format_findings(data['detailed_findings']['missing_validation'])
    
    scan_errors_html = '<p class="no-findings">No errors during scan.</p>'
    if data['detailed_findings']['errors']:
        error_list = [f'''<p class="finding-item MEDIUM"><strong>Error:</strong> {err}</p>''' for err in data['detailed_findings']['errors']]
        scan_errors_html = '\
'.join(error_list)


    final_html = template.replace('{{ total_critical }}', str(total_critical))
    final_html = final_html.replace('{{ total_high }}', str(total_high))
    final_html = final_html.replace('{{ total_medium }}', str(total_medium))
    final_html = final_html.replace('{{ hardcoded_secrets_findings }}', hardcoded_secrets_html)
    final_html = final_html.replace('{{ sensitive_files_findings }}', sensitive_files_html)
    final_html = final_html.replace('{{ exposed_bindings_findings }}', exposed_bindings_html)
    final_html = final_html.replace('{{ eval_exec_usage_findings }}', eval_exec_usage_html)
    final_html = final_html.replace('{{ missing_validation_findings }}', missing_validation_html)
    final_html = final_html.replace('{{ scan_errors }}', scan_errors_html)

    output_path = 'C:\\Veritas_Lab\\gravity-omega-v2\\backend\\security_dashboard.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Security dashboard generated at {output_path}")
    os.startfile(output_path) # Open in default browser

if __name__ == '__main__':
    generate_dashboard()
