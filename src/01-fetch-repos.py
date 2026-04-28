#!/usr/bin/env python3
import argparse
import csv
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
GITHUB_REPO_SEARCH_QUERY = "stars:>0 sort:stars"
DEFAULT_OUTPUT_FILE = "data/repos.csv"
DEFAULT_LIMIT = 200
ITEMS_PER_PAGE = 20
MIN_PULL_REQUESTS = 100
HTTP_MAX_RETRIES = 5
HTTP_TIMEOUT_SECONDS = 60
BASE_FIELDS = [
    "nameWithOwner",
    "url",
    "stargazerCount",
    "primaryLanguage",
    "mergedAndClosedPRsCount",
]


def _get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não encontrado. "
            "Configure a variável de ambiente ou use um arquivo .env"
        )
    return token


def _load_query(query_file: Path) -> str:
    if not query_file.exists():
        raise FileNotFoundError(f"Query file not found: {query_file}")
    return query_file.read_text(encoding="utf-8")


def _compute_rate_limit_wait(headers: Any) -> int | None:
    remaining = headers.get("X-RateLimit-Remaining") if headers else None
    reset_at = headers.get("X-RateLimit-Reset") if headers else None
    if remaining == "0" and reset_at:
        try:
            return max(int(reset_at) - int(time.time()) + 1, 1)
        except ValueError:
            return None
    return None


def _run_graphql_query(token: str, query_template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps({"query": query_template, "variables": variables}).encode("utf-8")

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
            is_rate_limited = "rate limit" in messages.lower()
            if is_rate_limited and attempt < HTTP_MAX_RETRIES:
                wait_s = _compute_rate_limit_wait(headers)
                if wait_s is None:
                    wait_s = min(2 ** (attempt - 1), 32)
                print(
                    f"GraphQL rate limit reached, retrying in {wait_s}s "
                    f"(attempt {attempt}/{HTTP_MAX_RETRIES})...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                continue
            raise RuntimeError(messages)

        return data

    raise RuntimeError("Failed to fetch data from GitHub API after retries.")


def fetch_top_repositories(limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    token = _get_github_token()
    query_file = Path(__file__).with_name("github_query.graphql")
    query_template = _load_query(query_file)

    print(
        f"Fetching top repositories by stars until {limit} repositories with at least "
        f"{MIN_PULL_REQUESTS} merged/closed PRs are collected...",
        file=sys.stderr,
    )

    repositories: List[Dict[str, Any]] = []
    cursor = None
    page = 0

    while len(repositories) < limit:
        page += 1
        variables = {
            "first": ITEMS_PER_PAGE,
            "cursor": cursor,
            "queryString": GITHUB_REPO_SEARCH_QUERY,
        }
        data = _run_graphql_query(token, query_template, variables)
        search = data["data"]["search"]
        nodes = search.get("nodes", [])
        if not nodes:
            break

        accepted_in_page = 0
        for repo in nodes:
            pr_count = repo.get("pullRequests", {}).get("totalCount", 0)
            if pr_count < MIN_PULL_REQUESTS:
                continue
            repositories.append(repo)
            accepted_in_page += 1
            if len(repositories) >= limit:
                break

        print(
            f"Page {page}: accepted {accepted_in_page} repositories "
            f"({len(repositories)}/{limit})",
            file=sys.stderr,
        )

        if len(repositories) >= limit or not search["pageInfo"]["hasNextPage"]:
            break
        cursor = search["pageInfo"]["endCursor"]

    return repositories[:limit]


def _load_existing_metadata(output_file: Path) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    if not output_file.exists():
        return {}, []

    with open(output_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames or "nameWithOwner" not in reader.fieldnames:
            return {}, []

        extra_fields = [field for field in reader.fieldnames if field not in BASE_FIELDS]
        existing: Dict[str, Dict[str, str]] = {}
        for row in reader:
            name = row.get("nameWithOwner", "")
            if not name:
                continue
            existing[name] = {field: row.get(field, "") for field in extra_fields}
        return existing, extra_fields


def export_to_csv(
    repositories: List[Dict[str, Any]],
    output_file: Path,
    existing_by_repo: Dict[str, Dict[str, str]] | None = None,
    extra_fields: List[str] | None = None,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    existing_by_repo = existing_by_repo or {}
    extra_fields = extra_fields or []

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [*BASE_FIELDS, *extra_fields]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for repo in repositories:
            row = {
                "nameWithOwner": repo.get("nameWithOwner", ""),
                "url": repo.get("url", ""),
                "stargazerCount": repo.get("stargazerCount", 0),
                "primaryLanguage": repo.get("primaryLanguage", {}).get("name", "") if repo.get("primaryLanguage") else "",
                "mergedAndClosedPRsCount": repo.get("pullRequests", {}).get("totalCount", 0),
            }

            previous = existing_by_repo.get(row["nameWithOwner"], {})
            for field in extra_fields:
                row[field] = previous.get(field, "")

            writer.writerow(row)

    print(f"Exported {len(repositories)} repositories to {output_file}", file=sys.stderr)


def count_csv_rows(csv_file: Path) -> int:
    if not csv_file.exists():
        return 0

    with open(csv_file, "r", encoding="utf-8") as csvfile:
        return max(sum(1 for _ in csv.reader(csvfile)) - 1, 0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch top GitHub repositories by stars and export to CSV"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Number of repositories to fetch (default: {DEFAULT_LIMIT})",
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
        help="Force re-fetch even if output file already has enough repositories",
    )

    args = parser.parse_args()
    script_dir = Path(__file__).parent.parent
    output_file = Path(args.output)
    if not output_file.is_absolute():
        output_file = script_dir / output_file

    existing_by_repo, extra_fields = _load_existing_metadata(output_file)

    if not args.force:
        existing_count = count_csv_rows(output_file)
        if existing_count >= args.limit:
            print(
                f"CSV file already exists with {existing_count} repositories "
                f"(>= {args.limit} requested). Skipping fetch.",
                file=sys.stderr,
            )
            print("Use --force to re-fetch anyway.", file=sys.stderr)
            return
        if existing_count > 0:
            print(
                f"CSV file exists with only {existing_count} repositories "
                f"(< {args.limit} requested). Fetching data...",
                file=sys.stderr,
            )

    repositories = fetch_top_repositories(limit=args.limit)
    export_to_csv(
        repositories,
        output_file,
        existing_by_repo=existing_by_repo,
        extra_fields=extra_fields,
    )


if __name__ == "__main__":
    main()
