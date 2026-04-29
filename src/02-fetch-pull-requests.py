#!/usr/bin/env python3
import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Tuple
import urllib.error
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GITHUB_API_URL = "https://api.github.com/graphql"
DEFAULT_INPUT_FILE = "data/repos.csv"
DEFAULT_OUTPUT_FILE = "data/pull_requests.csv"
DEFAULT_MAX_PRS_PER_REPO = 200
DEFAULT_PAGE_SIZE = 50
DEFAULT_REPO_DELAY_SECONDS = 0.5
MIN_REVIEW_COUNT = 1
MIN_DURATION_HOURS = 1.0
HTTP_MAX_RETRIES = 5
HTTP_TIMEOUT_SECONDS = 60
OUTPUT_FIELDS = [
    "repo",
    "state",
    "created_at",
    "closed_at",
    "time_to_close_hours",
    "changed_files",
    "additions",
    "deletions",
    "body_length",
    "participants_count",
    "comments_count",
    "reviews_count",
]
PULL_REQUEST_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      first: 50,
      after: $cursor,
      states: [MERGED, CLOSED],
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      pageInfo {
        endCursor
        hasNextPage
      }
      nodes {
        number
        title
        state
        createdAt
        mergedAt
        closedAt
        additions
        deletions
        changedFiles
        bodyText
        participants {
          totalCount
        }
        comments {
          totalCount
        }
        reviews(first: 1) {
          totalCount
        }
      }
    }
  }
}
""".strip()


def _get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não encontrado. "
            "Configure a variável de ambiente ou use um arquivo .env"
        )
    return token


def _compute_rate_limit_wait(headers: Any) -> int | None:
    remaining = headers.get("X-RateLimit-Remaining") if headers else None
    reset_at = headers.get("X-RateLimit-Reset") if headers else None
    if remaining == "0" and reset_at:
        try:
            return max(int(reset_at) - int(time.time()) + 1, 1)
        except ValueError:
            return None
    return None


def _run_graphql_query(token: str, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")

    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        request = urllib.request.Request(
            GITHUB_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                data = json.load(response)
                headers = response.headers
        except urllib.error.HTTPError as exc:
            wait_s = _compute_rate_limit_wait(exc.headers)
            should_retry = exc.code in {403, 429} or exc.code >= 500
            if should_retry and attempt < HTTP_MAX_RETRIES:
                if wait_s is None:
                    wait_s = min(2 ** (attempt - 1), 32)
                print(
                    f"GitHub API error {exc.code}, retrying in {wait_s}s "
                    f"(attempt {attempt}/{HTTP_MAX_RETRIES})...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                continue
            raise RuntimeError(exc.read().decode("utf-8", errors="replace")) from exc
        except urllib.error.URLError as exc:
            if attempt < HTTP_MAX_RETRIES:
                wait_s = min(2 ** (attempt - 1), 32)
                print(
                    f"Network error ({exc.reason}), retrying in {wait_s}s "
                    f"(attempt {attempt}/{HTTP_MAX_RETRIES})...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                continue
            raise RuntimeError(f"Network error during GitHub query: {exc.reason}") from exc

        if data.get("errors"):
            messages = "; ".join(error.get("message", "Unknown GraphQL error") for error in data["errors"])
            lowered = messages.lower()
            should_retry = "rate limit" in lowered or "something went wrong" in lowered or "timeout" in lowered
            if should_retry and attempt < HTTP_MAX_RETRIES:
                wait_s = _compute_rate_limit_wait(headers)
                if wait_s is None:
                    wait_s = min(2 ** (attempt - 1), 32)
                print(
                    f"GraphQL error '{messages}', retrying in {wait_s}s "
                    f"(attempt {attempt}/{HTTP_MAX_RETRIES})...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                continue
            raise RuntimeError(messages)

        return data

    raise RuntimeError("Failed to fetch data from GitHub API after retries.")


def _parse_repo_name(repo_name: str) -> Tuple[str, str]:
    parts = repo_name.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid repository name: {repo_name}")
    return parts[0], parts[1]


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_pull_requests_for_repo(
    token: str,
    repo_name: str,
    max_prs_per_repo: int = DEFAULT_MAX_PRS_PER_REPO,
) -> List[Dict[str, Any]]:
    owner, name = _parse_repo_name(repo_name)
    pull_requests: List[Dict[str, Any]] = []
    cursor = None
    page = 0

    while len(pull_requests) < max_prs_per_repo:
        page += 1
        data = _run_graphql_query(
            token,
            PULL_REQUEST_QUERY,
            {"owner": owner, "name": name, "cursor": cursor},
        )
        repository = data.get("data", {}).get("repository")
        if repository is None:
            raise RuntimeError(f"Repository not found or unavailable: {repo_name}")

        connection = repository["pullRequests"]
        nodes = connection.get("nodes", [])
        if not nodes:
            break

        remaining = max_prs_per_repo - len(pull_requests)
        pull_requests.extend(nodes[:remaining])
        print(
            f"    page {page}: fetched {len(pull_requests)}/{max_prs_per_repo} PRs",
            file=sys.stderr,
        )

        if len(pull_requests) >= max_prs_per_repo or not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]

    return pull_requests[:max_prs_per_repo]


def _build_pull_request_row(repo_name: str, pr: Dict[str, Any]) -> Dict[str, Any] | None:
    reviews_count = pr.get("reviews", {}).get("totalCount", 0)
    if reviews_count < MIN_REVIEW_COUNT:
        return None

    created_at = pr.get("createdAt")
    closed_at = pr.get("mergedAt") or pr.get("closedAt")
    created_dt = _parse_iso8601(created_at)
    closed_dt = _parse_iso8601(closed_at)
    if created_dt is None or closed_dt is None:
        return None

    time_to_close_hours = (closed_dt - created_dt).total_seconds() / 3600.0
    if time_to_close_hours < MIN_DURATION_HOURS:
        return None

    return {
        "repo": repo_name,
        "state": pr.get("state", ""),
        "created_at": created_at or "",
        "closed_at": closed_at or "",
        "time_to_close_hours": f"{time_to_close_hours:.4f}",
        "changed_files": pr.get("changedFiles", 0),
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "body_length": len(pr.get("bodyText") or ""),
        "participants_count": pr.get("participants", {}).get("totalCount", 0),
        "comments_count": pr.get("comments", {}).get("totalCount", 0),
        "reviews_count": reviews_count,
    }


def filter_pull_requests(repo_name: str, pull_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered_rows: List[Dict[str, Any]] = []
    for pr in pull_requests:
        row = _build_pull_request_row(repo_name, pr)
        if row is not None:
            filtered_rows.append(row)
    return filtered_rows


def load_repositories(csv_file: Path) -> List[Dict[str, str]]:
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    repos: List[Dict[str, str]] = []
    with open(csv_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            repos.append(row)
    return repos


def save_repositories(csv_file: Path, repos: List[Dict[str, str]]) -> None:
    if not repos:
        return

    fieldnames = list(repos[0].keys())
    if "prDataCollected" not in fieldnames:
        fieldnames.append("prDataCollected")

    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(repos)


def load_existing_pull_request_rows(output_file: Path) -> Dict[str, List[Dict[str, str]]]:
    if not output_file.exists():
        return {}

    rows_by_repo: Dict[str, List[Dict[str, str]]] = {}
    with open(output_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            repo_name = row.get("repo", "")
            if not repo_name:
                continue
            rows_by_repo.setdefault(repo_name, []).append(row)
    return rows_by_repo


def save_pull_request_rows(output_file: Path, rows_by_repo: Dict[str, List[Dict[str, Any]]]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for repo_name in sorted(rows_by_repo.keys()):
            for row in rows_by_repo[repo_name]:
                writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch pull requests for repositories listed in repos.csv"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT_FILE,
        help=f"Input CSV file with repositories (default: {DEFAULT_INPUT_FILE})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-collect pull requests even if a repository was already processed",
    )
    parser.add_argument(
        "--max-prs-per-repo",
        type=int,
        default=DEFAULT_MAX_PRS_PER_REPO,
        help=(
            "Maximum number of pull requests to collect per repository "
            f"(default: {DEFAULT_MAX_PRS_PER_REPO})"
        ),
    )
    parser.add_argument(
        "--limit-repos",
        type=int,
        default=None,
        help="Limit how many repositories will be processed (useful for testing)",
    )

    args = parser.parse_args()
    script_dir = Path(__file__).parent.parent

    input_file = Path(args.input)
    if not input_file.is_absolute():
        input_file = script_dir / input_file

    output_file = Path(args.output)
    if not output_file.is_absolute():
        output_file = script_dir / output_file

    token = _get_github_token()
    repos = load_repositories(input_file)
    rows_by_repo: Dict[str, List[Dict[str, Any]]] = {} if args.force else load_existing_pull_request_rows(output_file)

    if args.force:
        for repo in repos:
            repo["prDataCollected"] = "false"
    else:
        for repo in repos:
            repo.setdefault("prDataCollected", "")

    pending_repos = [repo for repo in repos if repo.get("prDataCollected", "").lower() != "true"]
    if args.limit_repos is not None:
        pending_repos = pending_repos[:args.limit_repos]

    if not pending_repos:
        print("No repositories to process", file=sys.stderr)
        return

    print(
        f"Processing {len(pending_repos)} repositories with up to "
        f"{args.max_prs_per_repo} PRs per repository",
        file=sys.stderr,
    )

    for index, repo in enumerate(pending_repos, start=1):
        repo_name = repo.get("nameWithOwner", "")
        print(f"[{index}/{len(pending_repos)}] {repo_name}", file=sys.stderr)
        rows_by_repo.pop(repo_name, None)

        try:
            pull_requests = fetch_pull_requests_for_repo(
                token,
                repo_name,
                max_prs_per_repo=args.max_prs_per_repo,
            )
            filtered_rows = filter_pull_requests(repo_name, pull_requests)
            rows_by_repo[repo_name] = filtered_rows
            repo["prDataCollected"] = "true"
            print(
                f"  collected {len(pull_requests)} PRs, kept {len(filtered_rows)} after filters",
                file=sys.stderr,
            )
        except Exception as exc:
            repo["prDataCollected"] = "false"
            print(f"  failed: {exc}", file=sys.stderr)
        finally:
            save_repositories(input_file, repos)
            save_pull_request_rows(output_file, rows_by_repo)
            time.sleep(DEFAULT_REPO_DELAY_SECONDS)

    processed = sum(1 for repo in repos if repo.get("prDataCollected", "").lower() == "true")
    print(f"Finished. Repositories with prDataCollected=true: {processed}/{len(repos)}", file=sys.stderr)
    print(
        f"Saved {sum(len(rows) for rows in rows_by_repo.values())} filtered pull requests to {output_file}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
