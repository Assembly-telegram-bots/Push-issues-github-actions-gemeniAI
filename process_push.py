import os
import json
import requests
from github import Github, Auth

gh_token = os.environ.get("GITHUB_TOKEN")
gemini_key = os.environ.get("GEMINI_API_KEY")
repo_name = os.environ.get("REPOSITORY")
commit_sha = os.environ.get("COMMIT_SHA")
allowed_user = os.environ.get("ALLOWED_USER").strip().lower()

auth = Auth.Token(gh_token)
gh = Github(auth=auth)
repo = gh.get_repo(repo_name)
commit = repo.get_commit(commit_sha)

if commit.author and commit.author.login.strip().lower() != allowed_user:
    exit(0)

diff_text = ""
for file in commit.files:
    diff_text += f"File: {file.filename}\nPatch:\n{file.patch}\n\n"
    if len(diff_text) > 100000:
        diff_text += "\n[Diff too large, truncated...]"
        break

prompt = f"""
Analyze this Git commit and create a detailed description for a GitHub Issue explaining what was changed.
Commit Message: {commit.commit.message}

Code Changes:
{diff_text}

Return only a raw JSON object with no markdown formatting. The JSON must contain these exact keys:
"issue_title": string,
"issue_body": string
"""

model_name = "gemini-2.5-flash"
api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
payload = {"contents": [{"parts": [{"text": prompt}]}]}
headers = {"Content-Type": "application/json"}

resp = requests.post(api_url, json=payload, headers=headers)
resp_data = resp.json()

response_text = resp_data['candidates'][0]['content']['parts'][0]['text'].strip()

if response_text.startswith("```json"):
    response_text = response_text[7:]
elif response_text.startswith("```"):
    response_text = response_text[3:]
    
if response_text.endswith("```"):
    response_text = response_text[:-3]
    
response_text = response_text.strip()
result = json.loads(response_text)

repo.create_issue(
    title=result['issue_title'],
    body=f"{result['issue_body']}\n\n---\n*Сгенерировано на основе коммита {commit_sha[:7]}*"
)
