from urllib.parse import urlparse

import httpx


CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".cs", ".php", ".rb", ".swift", ".sql", ".html", ".css"}


def repo_parts(repo_url: str) -> tuple[str, str] | None:
    parsed = urlparse(repo_url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"} or len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not all(value and value not in {".", ".."} and all(char.isalnum() or char in "-_." for char in value) for value in (owner, repo)):
        return None
    return owner, repo


async def github_project_sources(repo_url: str, token: str = "") -> list[tuple[str, str, str]]:
    parts = repo_parts(repo_url)
    if not parts:
        return []
    owner, repo = parts
    headers = {"User-Agent": "JudgeX-Repository-Ingest/1.0", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    root = f"https://api.github.com/repos/{owner}/{repo}"
    output: list[tuple[str, str, str]] = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        response = await client.get(root, headers=headers)
        if response.status_code != 200:
            return output
        metadata = response.json()
        if metadata.get("private"):
            return output
        details = "\n".join(f"{key}: {metadata.get(key)}" for key in ("full_name", "description", "language", "default_branch", "created_at", "updated_at", "pushed_at", "stargazers_count", "forks_count", "open_issues_count", "license"))
        output.append(("repository_metadata", "GitHub repository metadata", details))

        readme_response = await client.get(f"{root}/readme", headers=headers)
        if readme_response.status_code == 200:
            download_url = readme_response.json().get("download_url", "")
            parsed_download = urlparse(download_url)
            if parsed_download.scheme == "https" and parsed_download.hostname == "raw.githubusercontent.com":
                raw = await client.get(download_url, headers={"User-Agent": headers["User-Agent"]})
                if raw.status_code == 200:
                    output.append(("readme", "README.md", raw.content[:2_000_000].decode("utf-8", errors="replace")))

        commit_response = await client.get(f"{root}/commits", params={"per_page": 12}, headers=headers)
        if commit_response.status_code == 200:
            commits = commit_response.json()
            if isinstance(commits, list):
                messages = []
                for commit in commits[:12]:
                    data = commit.get("commit", {})
                    messages.append(f"{data.get('author', {}).get('date', '')}: {data.get('message', '').splitlines()[0][:300]}")
                if messages:
                    output.append(("commit_history", "Recent commit messages", "\n".join(messages)))

        branch = metadata.get("default_branch", "main")
        tree = await client.get(f"{root}/git/trees/{branch}", params={"recursive": "1"}, headers=headers)
        if tree.status_code == 200:
            rows = tree.json().get("tree", [])
            candidates = [row for row in rows if row.get("type") == "blob" and row.get("size", 0) <= 100_000
                and any(row.get("path", "").lower().endswith(ext) for ext in CODE_EXTENSIONS)
                and row.get("path", "").count("/") <= 4]
            for row in candidates[:6]:
                path = row.get("path", "")
                file_response = await client.get(f"{root}/contents/{path}", params={"ref": branch}, headers=headers)
                if file_response.status_code != 200:
                    continue
                download_url = file_response.json().get("download_url", "")
                parsed_download = urlparse(download_url)
                if parsed_download.scheme != "https" or parsed_download.hostname != "raw.githubusercontent.com":
                    continue
                raw = await client.get(download_url, headers={"User-Agent": headers["User-Agent"]})
                if raw.status_code == 200:
                    output.append(("source_file", path, raw.content[:100_000].decode("utf-8", errors="replace")))
    return output
