#!/usr/bin/env python3
"""
awesome-english-ebooks Downloader Script
Fetches The Economist, The New Yorker, The Atlantic, and WIRED magazines from:
https://github.com/hehonghui/awesome-english-ebooks
"""

import sys
import os
import re
import json
import time
import socket
import shutil
import argparse
import subprocess
import urllib.request
import urllib.error

REPO_OWNER = "hehonghui"
REPO_NAME = "awesome-english-ebooks"
REPO_BRANCH = "master"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"
API_TREE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{REPO_BRANCH}?recursive=1"

MAGAZINE_PREFIXES = {
    "economist": "01_economist",
    "the-economist": "01_economist",
    "new_yorker": "02_new_yorker",
    "the-new-yorker": "02_new_yorker",
    "atlantic": "04_atlantic",
    "the-atlantic": "04_atlantic",
    "wired": "05_wired",
}

DEFAULT_PROXIES = [1082, 7890, 7897, 1087, 10808, 1080]
CACHE_DIR = os.path.expanduser("~/.cache/awesome_english_ebooks")
CACHE_FILE = os.path.join(CACHE_DIR, "tree_cache.json")
BUNDLED_SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tree_snapshot.json")
CACHE_TTL = 3600  # 1 hour


def detect_proxy():
    """Detect configured environment proxy or common local proxies."""
    for env_var in ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"]:
        val = os.environ.get(env_var)
        if val:
            return val

    for port in DEFAULT_PROXIES:
        s = socket.socket()
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    return None


def fetch_url_text(url, timeout=20):
    """Fetch text content using curl (fallback to urllib)."""
    proxy = detect_proxy()
    if shutil.which("curl"):
        cmd = ["curl", "-sSL", "--max-time", str(timeout)]
        if proxy:
            cmd.extend(["--proxy", proxy])
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if github_token and "api.github.com" in url:
            cmd.extend(["-H", f"Authorization: token {github_token}"])
        cmd.extend(["-H", "User-Agent: Mozilla/5.0", url])

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and res.stdout:
            return res.stdout.decode("utf-8", errors="replace")

    # Fallback to urllib
    proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy else urllib.request.ProxyHandler()
    opener = urllib.request.build_opener(proxy_handler)
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_cached_tree(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            t = data.get("tree", [])
            if t:
                return t, data.get("timestamp", 0)
        except Exception:
            pass
    return None, 0


def fetch_tree(refresh=False):
    """Fetch repository git tree, using cache when available and fallbacks on error."""
    cached_tree, ts = load_cached_tree(CACHE_FILE)
    if not refresh and cached_tree and (time.time() - ts < CACHE_TTL):
        return cached_tree

    # Attempt fetching from GitHub API
    try:
        content = fetch_url_text(API_TREE_URL)
        if content:
            data = json.loads(content)
            tree = data.get("tree", [])
            if tree and isinstance(tree, list) and len(tree) > 0:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": time.time(), "tree": tree}, f)
                return tree
    except Exception:
        pass

    # Fallback tier 1: existing user cache
    if cached_tree:
        return cached_tree

    # Fallback tier 2: bundled snapshot
    bundled_tree, _ = load_cached_tree(BUNDLED_SNAPSHOT)
    if bundled_tree:
        return bundled_tree

    raise RuntimeError("Failed to fetch repository tree and no cached snapshot is available.")


def parse_issues(tree, magazine="economist"):
    """Parse issues from git tree for a given magazine."""
    prefix = MAGAZINE_PREFIXES.get(magazine.lower(), "01_economist")
    issues = {}

    for item in tree:
        path = item.get("path", "")
        if not path.startswith(prefix + "/"):
            continue

        ext_match = re.search(r"\.(epub|mobi|pdf)$", path, re.IGNORECASE)
        if not ext_match:
            continue
        ext = ext_match.group(1).lower()

        # Find date pattern YYYY.MM.DD or YYYY.MM
        date_match = re.search(r"(\d{4})[._](\d{2})[._](\d{2})", path)
        if date_match:
            y, m, d = date_match.groups()
            date_key = f"{y}.{m}.{d}"
            year = y
        else:
            date_match_m = re.search(r"(\d{4})[._](\d{2})", path)
            if date_match_m:
                y, m = date_match_m.groups()
                date_key = f"{y}.{m}"
                year = y
            else:
                continue

        if date_key not in issues:
            issues[date_key] = {
                "date": date_key,
                "year": year,
                "folder": os.path.dirname(path),
                "files": {},
            }
        issues[date_key]["files"][ext] = {
            "path": path,
            "size": item.get("size", 0),
            "filename": os.path.basename(path),
            "raw_url": f"{RAW_BASE_URL}/{path}",
        }

    sorted_dates = sorted(issues.keys(), reverse=True)
    return [issues[d] for d in sorted_dates]


def normalize_issue_query(query, issues):
    """Normalize user input like 'latest', '2026.11.07', '11.07', '2026-11-07' to a matched issue."""
    if not issues:
        return None
    if not query or query.lower() == "latest":
        return issues[0]

    q_clean = query.replace("-", ".").replace("_", ".").strip()
    for issue in issues:
        if issue["date"] == q_clean:
            return issue
    for issue in issues:
        if issue["date"].endswith(q_clean):
            return issue
    q_digits = re.sub(r"\D", "", query)
    for issue in issues:
        if re.sub(r"\D", "", issue["date"]) == q_digits:
            return issue
        if re.sub(r"\D", "", issue["date"]).endswith(q_digits):
            return issue
    return None


def download_file(url, dest_path):
    """Download file with curl (with mirror fallback)."""
    proxy = detect_proxy()
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

    urls_to_try = [
        url,
        f"https://ghfast.top/{url}",
        f"https://mirror.ghproxy.com/{url}",
        f"https://ghproxy.net/{url}",
    ]

    temp_path = dest_path + ".tmp"
    last_error = None

    for attempt_url in urls_to_try:
        try:
            if shutil.which("curl"):
                cmd = ["curl", "-L", "-sS", "--fail", "--connect-timeout", "10", "--max-time", "120"]
                if proxy:
                    cmd.extend(["--proxy", proxy])
                cmd.extend(["-o", temp_path, attempt_url])
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    os.replace(temp_path, dest_path)
                    return True
                last_error = res.stderr.decode("utf-8", errors="replace")
            else:
                proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy}) if proxy else urllib.request.ProxyHandler()
                opener = urllib.request.build_opener(proxy_handler)
                req = urllib.request.Request(attempt_url, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(req, timeout=40) as resp, open(temp_path, "wb") as f:
                    shutil.copyfileobj(resp, f)
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    os.replace(temp_path, dest_path)
                    return True
        except Exception as e:
            last_error = str(e)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            continue

    raise RuntimeError(f"All download mirrors failed. Last error: {last_error}")


def format_size(bytes_num):
    if not bytes_num:
        return "Unknown size"
    if bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    return f"{bytes_num / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(description="Download The Economist & other magazines from awesome-english-ebooks")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List available issues")
    list_parser.add_argument("--magazine", "-m", default="economist", choices=list(MAGAZINE_PREFIXES.keys()), help="Magazine to list (default: economist)")
    list_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of issues to display (default: 10)")
    list_parser.add_argument("--year", "-y", type=str, default=None, help="Filter by year, e.g. 2026, 2025")
    list_parser.add_argument("--refresh", action="store_true", help="Force refresh git tree cache")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # download command
    down_parser = subparsers.add_parser("download", help="Download a magazine issue")
    down_parser.add_argument("--magazine", "-m", default="economist", choices=list(MAGAZINE_PREFIXES.keys()), help="Magazine to download (default: economist)")
    down_parser.add_argument("--issue", "-i", default="latest", help="Issue date (e.g. 'latest', '2026.11.07', '11.07')")
    down_parser.add_argument("--format", "-f", default="epub", choices=["epub", "mobi", "pdf", "all"], help="Format to download (default: epub)")
    down_parser.add_argument("--out-dir", "-o", default=None, help="Output directory (default: ./downloads/<magazine>)")
    down_parser.add_argument("--refresh", action="store_true", help="Force refresh git tree cache")
    down_parser.add_argument("--json", action="store_true", help="Output result as JSON")

    # latest shortcut command
    latest_parser = subparsers.add_parser("latest", help="Quickly download the latest issue in EPUB format")
    latest_parser.add_argument("--magazine", "-m", default="economist", choices=list(MAGAZINE_PREFIXES.keys()), help="Magazine name")
    latest_parser.add_argument("--format", "-f", default="epub", choices=["epub", "mobi", "pdf", "all"], help="Format")
    latest_parser.add_argument("--out-dir", "-o", default=None, help="Output directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd = args.command
    if cmd == "latest":
        cmd = "download"
        args.issue = "latest"
        args.refresh = False
        args.json = False

    try:
        tree = fetch_tree(refresh=args.refresh)
    except Exception as e:
        print(f"Error fetching catalog: {e}", file=sys.stderr)
        sys.exit(1)

    issues = parse_issues(tree, magazine=args.magazine)

    if cmd == "list":
        if args.year:
            issues = [i for i in issues if i["year"] == str(args.year)]
        filtered = issues[: args.limit] if args.limit > 0 else issues

        if args.json:
            print(json.dumps(filtered, indent=2, ensure_ascii=False))
            return

        print(f"\n📚 Available Issues for {args.magazine.upper()} (Total: {len(issues)})")
        print("─" * 60)
        for issue in filtered:
            fmts = []
            for fmt in ["epub", "mobi", "pdf"]:
                if fmt in issue["files"]:
                    sz = format_size(issue["files"][fmt]["size"])
                    fmts.append(f"{fmt.upper()} ({sz})")
            print(f"  📅 {issue['date']} : {', '.join(fmts)}")
        print("─" * 60)
        print("Tip: Run `python3 fetch_magazine.py download -i latest -f epub` to download.")

    elif cmd == "download":
        matched = normalize_issue_query(args.issue, issues)
        if not matched:
            print(f"Error: Issue '{args.issue}' not found for {args.magazine}.", file=sys.stderr)
            if issues:
                print(f"Latest available issue is: {issues[0]['date']}", file=sys.stderr)
            sys.exit(1)

        out_dir = args.out_dir or os.path.join(".", "downloads", args.magazine)
        os.makedirs(out_dir, exist_ok=True)

        target_fmts = ["epub", "mobi", "pdf"] if args.format == "all" else [args.format]
        downloaded_files = []

        for fmt in target_fmts:
            if fmt not in matched["files"]:
                print(f"Warning: Format '{fmt}' not available for issue {matched['date']}.", file=sys.stderr)
                continue

            file_info = matched["files"][fmt]
            filename = file_info["filename"]
            dest_path = os.path.join(out_dir, filename)

            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
                print(f"✓ Already downloaded: {dest_path} ({format_size(os.path.getsize(dest_path))})")
                downloaded_files.append({"format": fmt, "path": os.path.abspath(dest_path), "status": "existing"})
                continue

            print(f"⬇ Downloading {args.magazine.upper()} ({matched['date']}) [{fmt.upper()}] ...")
            try:
                download_file(file_info["raw_url"], dest_path)
                print(f"✓ Successfully saved to: {dest_path} ({format_size(os.path.getsize(dest_path))})")
                downloaded_files.append({"format": fmt, "path": os.path.abspath(dest_path), "status": "downloaded"})
            except Exception as err:
                print(f"✗ Failed to download {fmt}: {err}", file=sys.stderr)

        if args.json:
            print(json.dumps({"issue": matched["date"], "results": downloaded_files}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
