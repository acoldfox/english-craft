#!/usr/bin/env python3
"""
AudioBook Bay (ABB) Search & Magnet Extractor for EnglishCraft
Searches English audiobooks on AudioBook Bay (audiobookbay.lu and mirror domains),
extracts narrator/author/format/bitrate metadata, and constructs login-free
BitTorrent magnet links from the page's Info Hash and tracker list.

Inspired by and references open-source projects:
  - Steellow/abb-get (https://github.com/Steellow/abb-get)
  - smythp/audiobook_bay_scraper (https://github.com/smythp/audiobook_bay_scraper)
  - JamesRy96/audiobookbay-automated (https://github.com/JamesRy96/audiobookbay-automated)
"""

import os
import sys
import re
import html
import json
import socket
import shutil
import argparse
import subprocess
import urllib.parse
import urllib.request

ABB_DOMAINS = [
    "audiobookbay.lu",
    "audiobookbay.is",
    "audiobookbay.nl",
    "audiobookbay.fi",
    "audiobookbay.li",
]

DEFAULT_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.dler.org:6969/announce",
    "http://tracker.bt4g.com:2095/announce",
]

DEFAULT_PROXIES = [1082, 7890, 7897, 1087, 10808, 1080]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def detect_proxy():
    """Detect local HTTP/HTTPS proxy from env or common ports."""
    for env_var in ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"]:
        val = os.environ.get(env_var)
        if val:
            return val
    for port in DEFAULT_PROXIES:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return f"http://127.0.0.1:{port}"
        except OSError:
            continue
    return None


def fetch_html(url, timeout=20):
    """Fetch HTML string from URL using curl (with urllib fallback)."""
    proxy = detect_proxy()
    if shutil.which("curl"):
        cmd = [
            "curl",
            "-L",
            "-sS",
            "--connect-timeout",
            "10",
            "--max-time",
            str(timeout),
            "-A",
            USER_AGENT,
        ]
        if proxy:
            cmd.extend(["--proxy", proxy])
        cmd.append(url)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and res.stdout:
            return res.stdout.decode("utf-8", errors="replace")

    try:
        proxy_handler = (
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            if proxy
            else urllib.request.ProxyHandler()
        )
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def clean_tag_text(raw):
    """Strip HTML tags and unescape HTML entities."""
    if not raw:
        return ""
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = html.unescape(txt).replace("\xa0", " ")
    return re.sub(r"\s+", " ", txt).strip()


def parse_search_html(raw_html, base_domain="audiobookbay.lu"):
    """Parse AudioBook Bay search results HTML into structured items."""
    if not raw_html:
        return []

    results = []
    # Split by <div class="post"> blocks
    post_blocks = re.split(r'<div class=["\']post["\']>', raw_html)[1:]

    for block in post_blocks:
        title_match = re.search(
            r'<div class=["\']postTitle["\']>\s*<h2>\s*<a href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            block,
            re.DOTALL | re.IGNORECASE,
        )
        if not title_match:
            continue

        rel_url, raw_title = title_match.groups()
        title = clean_tag_text(raw_title)
        if rel_url.startswith("http"):
            detail_url = rel_url
        else:
            detail_url = f"https://{base_domain}/{rel_url.lstrip('/')}"

        cat_match = re.search(r"Category:\s*(.*?)<br", block, re.DOTALL | re.IGNORECASE)
        category = clean_tag_text(cat_match.group(1)) if cat_match else ""

        lang_match = re.search(r"Language:\s*([^<\n]+)", block, re.IGNORECASE)
        language = clean_tag_text(lang_match.group(1)) if lang_match else "English"

        posted_match = re.search(r"Posted:\s*([^<]+)<br", block, re.IGNORECASE)
        posted = clean_tag_text(posted_match.group(1)) if posted_match else ""

        fmt_match = re.search(
            r"Format:\s*<span[^>]*>([^<]+)</span>", block, re.IGNORECASE
        )
        audio_format = clean_tag_text(fmt_match.group(1)) if fmt_match else "Unknown"

        bit_match = re.search(
            r"Bitrate:\s*<span[^>]*>([^<]+)</span>", block, re.IGNORECASE
        )
        bitrate = clean_tag_text(bit_match.group(1)) if bit_match else "Unknown"

        size_match = re.search(
            r"File Size:\s*<span[^>]*>([^<]+)</span>\s*([A-Za-z]+)",
            block,
            re.IGNORECASE,
        )
        file_size = (
            f"{clean_tag_text(size_match.group(1))} {clean_tag_text(size_match.group(2))}"
            if size_match
            else "Unknown"
        )

        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE)
        cover_url = img_match.group(1).strip() if img_match else ""

        results.append(
            {
                "title": title,
                "url": detail_url,
                "category": category,
                "language": language,
                "posted": posted,
                "format": audio_format,
                "bitrate": bitrate,
                "size": file_size,
                "cover_url": cover_url,
                "source": f"AudioBook Bay ({base_domain})",
            }
        )

    return results


def build_magnet_uri(info_hash, title, trackers=None):
    """Construct a standard BitTorrent magnet URI from info_hash, title, and trackers."""
    info_hash_clean = info_hash.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", info_hash_clean):
        raise ValueError(f"Invalid 40-char SHA1 Info Hash: {info_hash}")

    dn = urllib.parse.quote(title.strip() or "Audiobook")
    all_trackers = []
    seen = set()
    for tr in (trackers or []) + DEFAULT_TRACKERS:
        tr_s = tr.strip()
        if tr_s and tr_s not in seen:
            seen.add(tr_s)
            all_trackers.append(tr_s)

    tr_query = "".join(f"&tr={urllib.parse.quote(tr, safe='')}" for tr in all_trackers)
    return f"magnet:?xt=urn:btih:{info_hash_clean}&dn={dn}{tr_query}"


def parse_detail_html(raw_html, url=""):
    """Parse an AudioBook Bay detail page to extract metadata, Info Hash, and Magnet URI."""
    if not raw_html:
        raise RuntimeError("Empty HTML content from detail page")

    title_match = re.search(
        r'<div class=["\']postTitle["\']>\s*<h1[^>]*>(.*?)</h1>',
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    title = clean_tag_text(title_match.group(1)) if title_match else "Audiobook"

    author_match = re.search(
        r'<span class=["\']author["\'][^>]*>(.*?)</span>', raw_html, re.DOTALL | re.IGNORECASE
    )
    author = clean_tag_text(author_match.group(1)) if author_match else "Unknown"

    narrator_match = re.search(
        r'<span class=["\']narrator["\'][^>]*>(.*?)</span>', raw_html, re.DOTALL | re.IGNORECASE
    )
    narrator = clean_tag_text(narrator_match.group(1)) if narrator_match else "Unknown"

    fmt_match = re.search(
        r'<span class=["\']format["\'][^>]*>(.*?)</span>', raw_html, re.DOTALL | re.IGNORECASE
    )
    audio_format = clean_tag_text(fmt_match.group(1)) if fmt_match else "Unknown"

    bit_match = re.search(
        r'<span class=["\']bitrate["\'][^>]*>(.*?)</span>', raw_html, re.DOTALL | re.IGNORECASE
    )
    bitrate = clean_tag_text(bit_match.group(1)) if bit_match else "Unknown"

    abridged_match = re.search(
        r'<span class=["\']is_abridged["\'][^>]*>(.*?)</span>',
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    abridged = clean_tag_text(abridged_match.group(1)) if abridged_match else "Unabridged"

    size_match = re.search(
        r"<td>Combined File Size:</td>\s*<td>(.*?)</td>",
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    size_str = clean_tag_text(size_match.group(1)) if size_match else "Unknown"

    hash_match = re.search(
        r"<td>Info Hash:</td>\s*<td[^>]*>\s*([a-fA-F0-9]{40})\s*</td>",
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if not hash_match:
        # Fallback regex for any 40-hex hash near Info Hash
        hash_match = re.search(
            r"Info Hash:.*?([a-fA-F0-9]{40})", raw_html, re.DOTALL | re.IGNORECASE
        )
    if not hash_match:
        raise RuntimeError("Could not find a 40-character Info Hash on this AudioBook Bay page")

    info_hash = hash_match.group(1).lower()

    trackers = [
        clean_tag_text(m.group(1))
        for m in re.finditer(
            r"<td>Tracker:</td>\s*<td[^>]*>(.*?)</td>", raw_html, re.DOTALL | re.IGNORECASE
        )
        if clean_tag_text(m.group(1))
    ]

    desc_match = re.search(
        r'<div class=["\']desc["\'][^>]*>(.*?)</div>', raw_html, re.DOTALL | re.IGNORECASE
    )
    description = ""
    if desc_match:
        # Strip the first metadata paragraph inside desc
        desc_body = re.sub(r"^\s*<p[^>]*>.*?</p>", "", desc_match.group(1), count=1, flags=re.DOTALL | re.IGNORECASE)
        description = clean_tag_text(desc_body)

    magnet_uri = build_magnet_uri(info_hash, title, trackers=trackers)

    return {
        "title": title,
        "author": author,
        "narrator": narrator,
        "format": audio_format,
        "bitrate": bitrate,
        "abridged": abridged,
        "size": size_str,
        "info_hash": info_hash,
        "tracker_count": len(trackers) or len(DEFAULT_TRACKERS),
        "magnet": magnet_uri,
        "url": url,
        "description": description[:500] + ("..." if len(description) > 500 else ""),
    }


def search_audiobooks(query, limit=5, page=1, format_filter=None):
    """Search AudioBook Bay across mirror domains with automatic fallback."""
    # Note: AudioBook Bay requires lowercase search queries (?s=...), otherwise it redirects to homepage
    encoded_q = urllib.parse.quote_plus(query.strip().lower())

    for domain in ABB_DOMAINS:
        if page > 1:
            search_url = f"https://{domain}/page/{page}/?s={encoded_q}"
        else:
            search_url = f"https://{domain}/?s={encoded_q}"

        raw_html = fetch_html(search_url)
        if not raw_html or "archiveTitle" not in raw_html:
            continue

        items = parse_search_html(raw_html, base_domain=domain)
        if format_filter:
            fmt_upper = format_filter.strip().upper()
            items = [it for it in items if fmt_upper in it["format"].upper()]

        if items:
            return items[:limit]

    return []


def fetch_audiobook_detail(query_or_url, index=1, format_filter=None):
    """Fetch detail & magnet link from a direct ABB URL or by searching query."""
    q = query_or_url.strip()
    target_url = None

    if q.startswith("http://") or q.startswith("https://"):
        target_url = q
    elif q.startswith("/abss/") or q.startswith("abss/"):
        target_url = f"https://{ABB_DOMAINS[0]}/{q.lstrip('/')}"
    else:
        results = search_audiobooks(q, limit=max(index, 5), format_filter=format_filter)
        if not results:
            raise RuntimeError(f"No audiobooks found on AudioBook Bay matching '{q}'")
        chosen_idx = min(max(1, index), len(results)) - 1
        target_url = results[chosen_idx]["url"]

    raw_html = fetch_html(target_url)
    if not raw_html:
        # Try mirror domains if direct domain failed
        parsed = urllib.parse.urlsplit(target_url)
        for domain in ABB_DOMAINS:
            alt_url = f"https://{domain}{parsed.path}"
            raw_html = fetch_html(alt_url)
            if raw_html and "Info Hash" in raw_html:
                target_url = alt_url
                break

    if not raw_html:
        raise RuntimeError(f"Failed to fetch audiobook detail page: {target_url}")

    return parse_detail_html(raw_html, url=target_url)


def save_magnet_record(detail, out_dir="./downloads/audiobooks"):
    """Save audiobook metadata and .magnet file to local directory."""
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", detail["title"]).strip().replace(" ", "_")[:60] or "audiobook"
    magnet_path = os.path.join(out_dir, f"{slug}.magnet")
    json_path = os.path.join(out_dir, f"{slug}.json")

    with open(magnet_path, "w", encoding="utf-8") as f:
        f.write(detail["magnet"] + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(detail, f, indent=2, ensure_ascii=False)

    return magnet_path, json_path


def main():
    parser = argparse.ArgumentParser(
        description="Search English audiobooks and extract login-free Magnet links from AudioBook Bay"
    )
    subparsers = parser.add_subparsers(dest="command")

    # search
    s_parser = subparsers.add_parser("search", help="Search audiobooks on AudioBook Bay")
    s_parser.add_argument("query", help="Book title, author, or narrator keywords")
    s_parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    s_parser.add_argument("--page", "-p", type=int, default=1, help="Search result page (default: 1)")
    s_parser.add_argument("--format", "-f", choices=["mp3", "m4b", "MP3", "M4B"], help="Filter by audio format (MP3 or M4B)")
    s_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # magnet / info
    m_parser = subparsers.add_parser("magnet", help="Extract audiobook details & login-free Magnet link")
    m_parser.add_argument("query", help="Audiobook title/query or AudioBook Bay detail URL")
    m_parser.add_argument("--index", "-i", type=int, default=1, help="Select N-th search result (default: 1)")
    m_parser.add_argument("--format", "-f", choices=["mp3", "m4b", "MP3", "M4B"], help="Filter search by audio format (MP3 or M4B)")
    m_parser.add_argument("--output-dir", "-o", default="./downloads/audiobooks", help="Directory to save .magnet and .json metadata")
    m_parser.add_argument("--open", action="store_true", help="Open magnet link in system default BitTorrent client")
    m_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        results = search_audiobooks(args.query, limit=args.limit, page=args.page, format_filter=args.format)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return

        print(f"\n🎧 AudioBook Bay Search Results for '{args.query}' (Found: {len(results)})")
        print("─" * 72)
        if not results:
            print("  No audiobooks found. Try broader keywords.")
        for idx, item in enumerate(results, 1):
            print(f"  [{idx}] {item['title']}")
            print(
                f"      Format: {item['format']} ({item['bitrate']}) | Size: {item['size']} | Posted: {item['posted']}"
            )
            if item.get("category"):
                print(f"      Category: {item['category']}")
            print(f"      URL: {item['url']}")
        print("─" * 72)

    elif args.command == "magnet":
        try:
            detail = fetch_audiobook_detail(args.query, index=args.index, format_filter=args.format)
        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            sys.exit(1)

        magnet_path, json_path = save_magnet_record(detail, out_dir=args.output_dir)

        if args.json:
            detail["magnet_file"] = os.path.abspath(magnet_path)
            detail["metadata_file"] = os.path.abspath(json_path)
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            print(f"\n🎧 {detail['title']}")
            print("─" * 72)
            print(f"  Author:     {detail['author']}")
            print(f"  Narrator:   {detail['narrator']}")
            print(f"  Format:     {detail['format']} | Bitrate: {detail['bitrate']} | {detail['abridged']}")
            print(f"  File Size:  {detail['size']}")
            print(f"  Info Hash:  {detail['info_hash']}")
            print(f"  Detail URL: {detail['url']}")
            if detail.get("description"):
                print(f"  Summary:    {detail['description'][:180]}...")
            print("─" * 72)
            print(f"🧲 Magnet Link (Login-Free):\n{detail['magnet']}\n")
            print(f"✓ Saved magnet file to:   {magnet_path}")
            print(f"✓ Saved metadata JSON to: {json_path}")

        if args.open:
            opener_cmd = "open" if sys.platform == "darwin" else "xdg-open"
            if shutil.which(opener_cmd):
                subprocess.run([opener_cmd, detail["magnet"]], check=False)
                print(f"🚀 Launched magnet link in default torrent client ({opener_cmd}).")


if __name__ == "__main__":
    main()
