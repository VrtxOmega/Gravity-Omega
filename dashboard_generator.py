import json
import os

def generate_dashboard(data_file, template_file, output_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(template_file, 'r', encoding='utf-8') as f:
        template = f.read()

    # Prepare data for template
    total_api_surface_area = data.get('total_api_surface_area', 0)
    auth_coverage_percentage = data.get('auth_coverage_percentage', 0)
    error_handling_coverage_percentage = data.get('error_handling_coverage_percentage', 0)
    dead_endpoints_count = data.get('dead_endpoints_count', 0)
    orphan_calls_count = data.get('orphan_calls_count', 0)

    # Determine class for percentage colors
    auth_coverage_class = 'low' if auth_coverage_percentage < 50 else ''
    error_handling_coverage_class = 'low' if error_handling_coverage_percentage < 50 else ''

    # Generate list items for critical routes
    critical_routes_list_items = []
    if data.get('critical_routes_no_error_handling'):
        for route in data['critical_routes_no_error_handling']:
            critical_routes_list_items.append(
                f"<li class='critical-item'><strong>{route['http_methods'][0].upper()} {route['url_pattern']}</strong> <span>(Function: {route['function_name']}, Line: {route['line_number']})</span></li>"
            )
    else:
        critical_routes_list_items.append("<li class='no-items'>No critical routes found without error handling. Good job!</li>")
    critical_routes_html = "\n".join(critical_routes_list_items)

    # Generate list items for dead endpoints
    dead_endpoints_list_items = []
    if data.get('dead_endpoints'):
        for endpoint in data['dead_endpoints']:
            dead_endpoints_list_items.append(
                f"<li><strong>{endpoint['http_methods'][0].upper()} {endpoint['url_pattern']}</strong> <span>(Function: {endpoint['function_name']}, Line: {endpoint['line_number']})</span></li>"
            )
    else:
        dead_endpoints_list_items.append("<li class='no-items'>No dead endpoints found. All routes are being used!</li>")
    dead_endpoints_html = "\n".join(dead_endpoints_list_items)

    # Generate list items for orphan calls
    orphan_calls_list_items = []
    if data.get('orphan_calls'):
        for call in data['orphan_calls']:
            orphan_calls_list_items.append(
                f"<li class='orphan-item'><strong>{call['url']}</strong> <span>(File: {os.path.basename(call['file'])}, Line: {call['line_number']}, Type: {call['type']})</span></li>"
            )
    else:
        orphan_calls_list_items.append("<li class='no-items'>No orphan frontend calls found. All calls match a backend route!</li>")
    orphan_calls_html = "\n".join(orphan_calls_list_items)

    # Populate template
    filled_template = template.format(
        total_api_surface_area=total_api_surface_area,
        auth_coverage_percentage=auth_coverage_percentage,
        auth_coverage_class=auth_coverage_class,
        error_handling_coverage_percentage=error_handling_coverage_percentage,
        error_handling_coverage_class=error_handling_coverage_class,
        dead_endpoints_count=dead_endpoints_count,
        orphan_calls_count=orphan_calls_count,
        critical_routes_no_error_handling_list=critical_routes_html,
        dead_endpoints_list=dead_endpoints_html,
        orphan_calls_list=orphan_calls_html
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(filled_template)
    print(f"Dashboard generated and saved to {output_file}")

if __name__ == '__main__':
    data_file = r'C:\Veritas_Lab\gravity-omega-v2\api_intelligence_data.json'
    template_file = r'C:\Veritas_Lab\gravity-omega-v2\dashboard_template.html'
    output_file = r'C:\Veritas_Lab\gravity-omega-v2\api_intelligence_dashboard.html'

    if os.path.exists(data_file) and os.path.exists(template_file):
        generate_dashboard(data_file, template_file, output_file)
    else:
        print(f"Error: Missing one or both input files: {data_file}, {template_file}")
