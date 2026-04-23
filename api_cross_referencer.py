import json
import re
from urllib.parse import urlparse
import os # Added missing import

def cross_reference_api_data(backend_routes_file, frontend_calls_file):
    with open(backend_routes_file, 'r', encoding='utf-8') as f:
        backend_routes = json.load(f)
    
    with open(frontend_calls_file, 'r', encoding='utf-8') as f:
        frontend_calls = json.load(f)

    # Normalize frontend URLs for comparison
    # Remove leading/trailing slashes and query parameters for basic matching
    normalized_frontend_urls = set()
    for call in frontend_calls:
        parsed_url = urlparse(call['url'])
        # Consider only the path for matching, ignore scheme, netloc, query, fragment
        normalized_path = parsed_url.path.strip('/')
        # Also handle potential /api/ prefix if not already there
        if not normalized_path.startswith('api/') and normalized_path:
            normalized_path = 'api/' + normalized_path # Assume local API calls are prefixed with /api/
        normalized_frontend_urls.add(normalized_path)
        # Add original path as well for more flexible matching
        normalized_frontend_urls.add(parsed_url.path.strip('/'))

    # --- Metrics Calculation ---
    total_api_surface_area = len(backend_routes)
    auth_checked_routes = sum(1 for route in backend_routes if route['has_auth_check'])
    error_handled_routes = sum(1 for route in backend_routes if route['has_error_handling'])

    auth_coverage = (auth_checked_routes / total_api_surface_area * 100) if total_api_surface_area > 0 else 0
    error_handling_coverage = (error_handled_routes / total_api_surface_area * 100) if total_api_surface_area > 0 else 0

    # --- Dead Endpoints ---
    dead_endpoints = []
    backend_url_patterns = {route['url_pattern'].strip('/') for route in backend_routes}
    
    for route in backend_routes:
        backend_path = route['url_pattern'].strip('/')
        # Simple check: if the backend path is not directly in normalized frontend URLs
        # This is a basic check and might miss dynamic routes or more complex matching
        if backend_path not in normalized_frontend_urls:
            # Attempt a more flexible match for routes with path parameters (e.g., /api/item/<id>)
            # Convert Flask route pattern to a regex pattern
            flask_regex_pattern = re.sub(r'<[^>]+>', r'[^/]+', backend_path)
            matched = False
            for frontend_url in normalized_frontend_urls:
                if re.fullmatch(flask_regex_pattern, frontend_url):
                    matched = True
                    break
            if not matched:
                dead_endpoints.append(route)

    # --- Orphan Calls ---
    orphan_calls = []
    # Create a set of all possible backend URL patterns, including regex for dynamic routes
    backend_patterns_for_matching = set()
    for route in backend_routes:
        backend_patterns_for_matching.add(route['url_pattern'].strip('/'))
        # Add regex version for dynamic routes
        flask_regex_pattern = re.sub(r'<[^>]+>', r'[^/]+', route['url_pattern'].strip('/'))
        backend_patterns_for_matching.add(flask_regex_pattern)

    for call in frontend_calls:
        parsed_url = urlparse(call['url'])
        frontend_path = parsed_url.path.strip('/')
        
        is_orphan = True
        for backend_pattern in backend_patterns_for_matching:
            # Try direct match
            if frontend_path == backend_pattern:
                is_orphan = False
                break
            # Try regex match for dynamic routes
            try:
                if re.fullmatch(backend_pattern, frontend_path):
                    is_orphan = False
                    break
            except re.error:
                # If the backend_pattern is not a valid regex (e.g., just a static path),
                # re.fullmatch might raise an error if it contains special regex chars not escaped.
                # This is a fallback, direct match should cover static paths.
                pass

        if is_orphan:
            orphan_calls.append(call)

    # --- Critical Routes with No Error Handling ---
    critical_routes_no_error_handling = []
    critical_keywords = ['vault', 'provenance', 'external', 'net', 'api', 'config', 'system', 'security', 'admin']

    for route in backend_routes:
        if not route['has_error_handling']:
            # Check if URL pattern or function name contains critical keywords
            is_critical = False
            for keyword in critical_keywords:
                if keyword in route['url_pattern'].lower() or keyword in route['function_name'].lower():
                    is_critical = True
                    break
            
            if is_critical:
                critical_routes_no_error_handling.append(route)
    
    # Sort by perceived risk (e.g., by number of critical keywords found, or just take top 10)
    # For simplicity, we'll just take the first 10 if there are many.
    critical_routes_no_error_handling = critical_routes_no_error_handling[:10]


    results = {
        'total_api_surface_area': total_api_surface_area,
        'auth_coverage_percentage': round(auth_coverage, 2),
        'error_handling_coverage_percentage': round(error_handling_coverage, 2),
        'dead_endpoints_count': len(dead_endpoints),
        'dead_endpoints': dead_endpoints,
        'orphan_calls_count': len(orphan_calls),
        'orphan_calls': orphan_calls,
        'critical_routes_no_error_handling': critical_routes_no_error_handling
    }
    return results

if __name__ == '__main__':
    backend_routes_file = r'C:\Veritas_Lab\gravity-omega-v2\backend_routes.json'
    frontend_calls_file = r'C:\Veritas_Lab\gravity-omega-v2\frontend_calls.json'
    output_file = r'C:\Veritas_Lab\gravity-omega-v2\api_intelligence_data.json'

    if os.path.exists(backend_routes_file) and os.path.exists(frontend_calls_file):
        intelligence_data = cross_reference_api_data(backend_routes_file, frontend_calls_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(intelligence_data, f, indent=4)
        print(f"API intelligence cross-referencing complete. Data saved to {output_file}")
    else:
        print(f"Error: Missing one or both input files: {backend_routes_file}, {frontend_calls_file}")
