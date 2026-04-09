import json
import os

def generate_dashboard(data_path, template_path, output_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # General metrics
    template = template.replace('{total_modules}', str(data['total_modules']))
    template = template.replace('{total_internal_edges}', str(data['total_internal_edges']))

    # Top In-Degree
    top_in_degree_bars = []
    if data['top_in_degree']:
        max_in_degree = max(item[1] for item in data['top_in_degree'])
        for module, count in data['top_in_degree']:
            width_percent = (count / max_in_degree) * 100 if max_in_degree > 0 else 0
            top_in_degree_bars.append(f"""
                <div class="bar-chart-item">
                    <span class="bar-chart-label" title="{module}">{module}</span>
                    <div class="bar-chart-bar-container">
                        <div class="bar-chart-bar" style="width: {width_percent:.2f}%;">
                            <span class="bar-chart-value">{count}</span>
                        </div>
                    </div>
                </div>
            """)
    else:
        top_in_degree_bars.append("<div class='no-findings'>No modules found with incoming dependencies.</div>")
    template = template.replace('{top_in_degree_bars}', ''.join(top_in_degree_bars))

    # Top Out-Degree
    top_out_degree_bars = []
    if data['top_out_degree']:
        max_out_degree = max(item[1] for item in data['top_out_degree'])
        for module, count in data['top_out_degree']:
            width_percent = (count / max_out_degree) * 100 if max_out_degree > 0 else 0
            top_out_degree_bars.append(f"""\n                <div class="bar-chart-item">\n                    <span class="bar-chart-label" title="{module}">{module}</span>\n                    <div class="bar-chart-bar-container">\n                        <div class="bar-chart-bar" style="width: {width_percent:.2f}%;">\n                            <span class="bar-chart-value">{count}</span>\n                        </div>\n                    </div>\n                </div>\n            """)
    else:
        top_out_degree_bars.append("<div class='no-findings'>No modules found with outgoing dependencies.</div>")
    template = template.replace('{top_out_degree_bars}', ''.join(top_out_degree_bars))

    # Circular Dependencies
    circular_dependencies_list = []
    if data['circular_dependencies']:
        circular_dependencies_list.append("<ul>")
        for cycle in data['circular_dependencies']:
            circular_dependencies_list.append(f"<li>{' &rarr; '.join(cycle)}</li>")
        circular_dependencies_list.append("</ul>")
    else:
        circular_dependencies_list.append("<div class='no-findings'>No circular dependencies found. Good job!</div>")
    template = template.replace('{circular_dependencies_list}', ''.join(circular_dependencies_list))

    # Orphan Modules
    orphan_modules_list = []
    if data['orphan_modules']:
        orphan_modules_list.append("<ul>")
        for module in data['orphan_modules']:
            orphan_modules_list.append(f"<li>{module}</li>")
        orphan_modules_list.append("</ul>")
    else:
        orphan_modules_list.append("<div class='no-findings'>No orphan modules found.</div>")
    template = template.replace('{orphan_modules_list}', ''.join(orphan_modules_list))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"Dashboard generated at {output_path}")

if __name__ == "__main__":
    data_file = "C:\\Users\\rlope\\.veritas\\python_dependency_data.json"
    template_file = "C:\\Veritas_Lab\\gravity-omega-v2\\backend\\python_dependency_template.html"
    output_file = "C:\\Users\\rlope\\.veritas\\python_dependency_dashboard.html"
    generate_dashboard(data_file, template_file, output_file)
