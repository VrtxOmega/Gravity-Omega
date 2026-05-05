import os
import requests
import sys

def main():
    token_path = r"C:\Veritas_Lab\secret_manager_backup\CODEBERG_TOKEN.txt"
    if not os.path.exists(token_path):
        print(f"ERROR: Token file not found at {token_path}")
        sys.exit(1)
        
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()

    if not token:
        print("ERROR: Token is empty.")
        sys.exit(1)

    url = "https://codeberg.org/api/v1/user/repos"
    headers = {
        "accept": "application/json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": "sovereign-docs",
        "private": False,
        "description": "SOVEREIGN Docs — Sovereign Document Platform"
    }

    print(f"Creating repository 'sovereign-docs' on Codeberg...")
    repo_request = requests.post(url, json=payload, headers=headers)
    
    if repo_request.status_code in [201, 200]:
        print("Successfully created Codeberg repository!")
        print(repo_request.json().get('clone_url'))
    elif repo_request.status_code == 409:
        print("Repository already exists.")
    else:
        print(f"Failed to create repository: {repo_request.status_code}")
        print(repo_request.text)
        sys.exit(1)

if __name__ == "__main__":
    main()
