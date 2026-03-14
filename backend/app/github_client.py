"""
GitHub client — fetch issues and PRs from configured repos.
"""

from typing import Optional, List
from github import Github
from app.config import settings

gh = Github(settings.GITHUB_TOKEN) if settings.GITHUB_TOKEN else None


def fetch_issues_and_prs(repos: Optional[List[str]] = None, per_repo_limit: int = 30) -> List[dict]:
    """
    Fetch open issues and PRs from the given repos.
    Returns a normalized list of dicts.
    """
    if gh is None:
        raise RuntimeError("GITHUB_TOKEN not set")

    repo_list = repos or settings.GITHUB_REPOS
    results = []

    for repo_name in repo_list:
        try:
            repo = gh.get_repo(repo_name)
        except Exception as e:
            results.append({"error": f"Could not access {repo_name}: {e}"})
            continue

        # Fetch issues (includes PRs on GitHub API)
        for issue in repo.get_issues(state="all", sort="updated", direction="desc")[:per_repo_limit]:
            is_pr = issue.pull_request is not None
            pr_data = None

            if is_pr:
                try:
                    pr = repo.get_pull(issue.number)
                    pr_data = {
                        "merged": pr.merged,
                        "draft": pr.draft,
                        "mergeable_state": pr.mergeable_state,
                    }
                except Exception:
                    pr_data = {"merged": False, "draft": False}

            # Determine status
            if is_pr and pr_data:
                if pr_data["merged"]:
                    status = "Merged"
                elif issue.state == "closed":
                    status = "Closed"
                elif pr_data["draft"]:
                    status = "Open"
                else:
                    status = "Open"
                item_type = "Draft PR" if (pr_data and pr_data["draft"]) else "PR"
            else:
                status = "Closed" if issue.state == "closed" else "Open"
                item_type = "Issue"

            results.append({
                "title": issue.title,
                "repo": repo_name,
                "url": issue.html_url,
                "type": item_type,
                "status": status,
                "assignee": issue.assignee.login if issue.assignee else "",
                "labels": [l.name for l in issue.labels],
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "number": issue.number,
            })

    return results


def fetch_repo_info(repo_name: str) -> dict:
    """Fetch basic info about a repo."""
    if gh is None:
        raise RuntimeError("GITHUB_TOKEN not set")

    repo = gh.get_repo(repo_name)
    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "url": repo.html_url,
        "description": repo.description,
        "stars": repo.stargazers_count,
        "language": repo.language,
        "open_issues": repo.open_issues_count,
    }
