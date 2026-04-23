import subprocess
import json
import os
from datetime import datetime, timedelta

def run_git_command(command, cwd):
    # Wrap command for WSL execution
    wsl_command = f"wsl bash -c \"{command.replace('"', '\\\"')}\""
    try:
        result = subprocess.run(
            wsl_command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {command}")
        print(f"Stderr: {e.stderr}")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return ""

def collect_git_data(repo_path):
    data = {}

    # 1. Total commits and date range
    total_commits = run_git_command("git rev-list --count HEAD", repo_path)
    first_commit_date = run_git_command("git log --pretty=format:%ad --date=iso-strict --reverse | head -n 1", repo_path)
    last_commit_date = run_git_command("git log --pretty=format:%ad --date=iso-strict | head -n 1", repo_path)

    data["total_commits"] = int(total_commits) if total_commits.isdigit() else 0
    data["first_commit_date"] = first_commit_date.split('T')[0] if first_commit_date else "N/A"
    data["last_commit_date"] = last_commit_date.split('T')[0] if last_commit_date else "N/A"

    # 2. Top 10 most-changed files by commit frequency
    most_changed_files_raw = run_git_command("git log --pretty=format: --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -n 10", repo_path)
    data["most_changed_files"] = []
    for line in most_changed_files_raw.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            data["most_changed_files"].append({"count": int(parts[0]), "file": parts[1]})

    # 3. Commit activity by day of week
    day_of_week_raw = run_git_command("git log --pretty=format:%ad --date=format:%a | sort | uniq -c | sort -nr", repo_path)
    data["commit_activity_by_day"] = []
    for line in day_of_week_raw.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            data["commit_activity_by_day"].append({"day": parts[1], "count": int(parts[0])})
    
    # Ensure all days are present, even if 0 commits
    all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    current_days = {item["day"]: item["count"] for item in data["commit_activity_by_day"]}
    data["commit_activity_by_day"] = []
    for day in all_days:
        data["commit_activity_by_day"].append({"day": day, "count": current_days.get(day, 0)})


    # 4. Largest single-commit diffs
    # Using a more robust awk command for WSL, escaping properly
    largest_diff_awk_cmd = """git log --pretty=format:'%H' --numstat | awk 'BEGIN {commit_hash=\"\"; total_diff=0; max_diff=0; max_commit_hash=\"\"} /^commit / {if (commit_hash != \"\" && total_diff > max_diff) {max_diff=total_diff; max_commit_hash=commit_hash} commit_hash=$2; total_diff=0} NF==3 {total_diff+=$1+$2} END {if (total_diff > max_diff) {max_diff=total_diff; max_commit_hash=commit_hash} print max_diff, max_commit_hash}' | head -n 1"""
    largest_diff_raw = run_git_command(largest_diff_awk_cmd, repo_path)
    
    largest_diff_info = {"diff_size": 0, "commit_hash": "N/A", "files": []}
    if largest_diff_raw:
        parts = largest_diff_raw.split(maxsplit=1)
        if len(parts) == 2:
            diff_size = int(parts[0])
            commit_hash = parts[1]
            largest_diff_info["diff_size"] = diff_size
            largest_diff_info["commit_hash"] = commit_hash
            
            files_in_commit_raw = run_git_command(f"git show --name-only --pretty=format: {commit_hash}", repo_path)
            largest_diff_info["files"] = [f for f in files_in_commit_raw.splitlines() if f.strip()]
    data["largest_single_commit_diff"] = largest_diff_info

    # 5. Recent velocity - commits per week for the last 8 weeks
    velocity_raw = run_git_command("git log --since=\"8 weeks ago\" --pretty=format:\"%ad\" --date=format:\"%Y-%W\" | sort | uniq -c", repo_path)
    
    velocity_data = {}
    for line in velocity_raw.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            count = int(parts[0])
            year_week = parts[1] # e.g., 2024-10
            velocity_data[year_week] = count

    # Generate last 8 weeks and fill in missing data
    today = datetime.now()
    weeks = []
    for i in range(8):
        # Calculate the start of the current week (Monday)
        current_week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
        year = current_week_start.isocalendar()[0]
        week_num = current_week_start.isocalendar()[1]
        
        # Format as YYYY-WW
        year_week_str = f"{year}-{week_num:02d}"
        weeks.insert(0, {"week": year_week_str, "count": velocity_data.get(year_week_str, 0)})
    
    data["recent_velocity"] = weeks

    return data

if __name__ == "__main__":
    repo_path = "C:\\Veritas_Lab\\gravity-omega-v2" # Adjust if running from a different directory
    git_data = collect_git_data(repo_path)
    
    output_path = os.path.join(repo_path, "git_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(git_data, f, indent=4)
    print(f"Git data collected and saved to {output_path}")
