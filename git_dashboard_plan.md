# Git History Intelligence Dashboard Plan

## Goal
Generate a styled HTML dashboard for the `gravity-omega-v2` repository, displaying key Git history metrics.

## Steps
1.  **Create `collect_git_data.py`:** A Python script to execute Git commands and parse their output into a JSON file (`git_data.json`). This script will gather:
    *   Total commits and date range.
    *   Top 10 most-changed files by commit frequency.
    *   Commit activity by day of week.
    *   Largest single-commit diffs (lines added/deleted).
    *   Recent velocity (commits per week for the last 8 weeks).
2.  **Create `git_dashboard_template.html`:** An HTML template file with placeholders for the data.
3.  **Create `generate_git_dashboard.py`:** A Python script to read `git_data.json`, populate `git_dashboard_template.html`, and save the result as `git_dashboard.html`.
4.  **Execute `collect_git_data.py`:** Run the data collection script.
5.  **Execute `generate_git_dashboard.py`:** Run the dashboard generation script.
6.  **Open `git_dashboard.html`:** Launch the generated dashboard in the browser.

## Data Extraction Details
*   **Total Commits:** `git rev-list --count HEAD`
*   **Date Range:** `git log --pretty=format:%ad --date=iso-strict --reverse | head -n 1` (first) and `git log --pretty=format:%ad --date=iso-strict | head -n 1` (last).
*   **Most Changed Files:** `git log --pretty=format: --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -n 10`
*   **Commit Activity by Day:** `git log --pretty=format:%ad --date=format:%a | sort | uniq -c | sort -nr`
*   **Largest Diffs:** `git log --pretty=format:'%H' --numstat | awk 'BEGIN {commit_hash=""; total_diff=0; max_diff=0; max_commit_hash=""} /^commit / {if (commit_hash != "" && total_diff > max_diff) {max_diff=total_diff; max_commit_hash=commit_hash} commit_hash=$2; total_diff=0} NF==3 {total_diff+=$1+$2} END {if (total_diff > max_diff) {max_diff=total_diff; max_commit_hash=commit_hash} print max_diff, max_commit_hash}' | head -n 1` then `git show --name-only <hash>`.
*   **Recent Velocity:** `git log --since="8 weeks ago" --pretty=format:"%ad" --date=format:"%Y-%W" | sort | uniq -c` (will need to fill in missing weeks with 0s in Python).

## Styling Notes
*   VERITAS gold (#D4A843) accent on dark (#1a1a2e) background.
*   Roboto font via Google Fonts.
*   CSS grid cards, rounded corners (8px), subtle box-shadow.
*   Animated gauge bars for charts.
