import json
import os

def generate_dashboard(repo_path):
    data_file_path = os.path.join(repo_path, "git_data.json")
    template_file_path = os.path.join(repo_path, "git_dashboard_template.html")
    output_file_path = os.path.join(repo_path, "git_dashboard.html")

    try:
        with open(data_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {data_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {data_file_path}")
        return

    try:
        with open(template_file_path, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found at {template_file_path}")
        return

    # Prepare data for template
    total_commits = data.get("total_commits", 0)
    first_commit_date = data.get("first_commit_date", "N/A")
    last_commit_date = data.get("last_commit_date", "N/A")
    
    largest_diff = data.get("largest_single_commit_diff", {"diff_size": 0, "commit_hash": "N/A", "files": []})
    largest_diff_files_html = "".join([f"<li><code>{f}</code></li>" for f in largest_diff["files"]])

    # Replace placeholders in the template
    rendered_html = template.replace("{{ total_commits }}", str(total_commits))
    rendered_html = rendered_html.replace("{{ first_commit_date }}", first_commit_date)
    rendered_html = rendered_html.replace("{{ last_commit_date }}", last_commit_date)
    rendered_html = rendered_html.replace("{{ largest_diff.diff_size }}", str(largest_diff["diff_size"]))
    rendered_html = rendered_html.replace("{{ largest_diff.commit_hash }}", largest_diff["commit_hash"])
    rendered_html = rendered_html.replace("{{ largest_diff_files }}", largest_diff_files_html)
    
    # Inject the entire data JSON for JavaScript to use
    rendered_html = rendered_html.replace("{{ data_json }}", json.dumps(data, indent=2))

    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        print(f"Dashboard generated and saved to {output_file_path}")
    except Exception as e:
        print(f"Error writing dashboard file: {e}")

if __name__ == "__main__":
    repo_path = "C:\\Veritas_Lab\\gravity-omega-v2"
    generate_dashboard(repo_path)
