#!/usr/bin/env python3
"""
Public Domain Book Downloader for WordTower Importer
Supports Standard Ebooks & Project Gutenberg
"""

import sys
import os
import re
import json
import socket
import urllib.parse
import argparse
import subprocess
import xml.etree.ElementTree as ET
import zipfile

DEFAULT_PROXIES = [1082, 7890, 7897, 1087, 10808, 1080]


def detect_proxy():
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


def fetch_url(url, timeout=25):
    proxy = detect_proxy()
    cmd = ["curl", "-sSL", "--max-time", str(timeout), "--connect-timeout", "10"]
    if proxy:
        cmd.extend(["--proxy", proxy])
    cmd.extend(["-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", url])
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and res.stdout:
        return res.stdout
    return None


def search_standard_ebooks(query, limit=5):
    """Search Standard Ebooks OPDS catalog."""
    encoded = urllib.parse.quote(query)
    url = f"https://standardebooks.org/feeds/opds/all?query={encoded}"
    raw = fetch_url(url, timeout=15)
    if not raw:
        return []

    results = []
    try:
        tree = ET.fromstring(raw.decode("utf-8", errors="replace"))
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in tree.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip()
            author_el = entry.find("atom:author/atom:name", ns)
            author = author_el.text.strip() if author_el is not None and author_el.text else "Unknown"
            summary = entry.findtext("atom:summary", "", ns).strip()

            epub_url = None
            size_bytes = 0
            for link in entry.findall("atom:link", ns):
                typ = link.attrib.get("type", "")
                link_title = link.attrib.get("title", "").lower()
                if typ == "application/epub+zip" and "advanced" not in link_title:
                    epub_url = link.attrib.get("href", "")
                    try:
                        size_bytes = int(link.attrib.get("length", 0))
                    except ValueError:
                        size_bytes = 0
                    if epub_url:
                        sep = "&" if "?" in epub_url else "?"
                        if "source=download" not in epub_url:
                            epub_url = f"{epub_url}{sep}source=download"
                    break

            if epub_url:
                results.append({
                    "title": title,
                    "author": author,
                    "summary": summary,
                    "download_url": epub_url,
                    "size_bytes": size_bytes,
                    "source": "Standard Ebooks",
                })
            if len(results) >= limit:
                break
    except Exception:
        pass

    return results


def search_gutenberg(query, limit=5):
    """Search Project Gutenberg (official site with Gutendex fallback)."""
    encoded = urllib.parse.quote(query)
    # 1. Fast official Gutenberg search
    url = f"https://www.gutenberg.org/ebooks/search/?query={encoded}"
    raw = fetch_url(url, timeout=15)
    results = []

    if raw:
        html = raw.decode("utf-8", errors="replace")
        pattern = re.compile(
            r'<li class=\"booklink\">\s*<a class=\"link\" href=\"/ebooks/(\d+)\".*?<span class=\"title\">(.*?)</span>(?:\s*<span class=\"subtitle\">(.*?)</span>)?',
            re.DOTALL
        )
        for match in pattern.finditer(html):
            bid, title, author = match.groups()
            title_clean = title.strip()
            author_clean = author.strip() if author else "Unknown"
            epub_url = f"https://www.gutenberg.org/cache/epub/{bid}/pg{bid}.epub"
            results.append({
                "id": bid,
                "title": title_clean,
                "author": author_clean,
                "summary": f"Project Gutenberg eBook #{bid}",
                "download_url": epub_url,
                "size_bytes": 0,
                "source": "Project Gutenberg",
            })
            if len(results) >= limit:
                break

    # 2. Fallback to Gutendex if needed
    if not results:
        api_url = f"https://gutendex.com/books?search={encoded}"
        api_raw = fetch_url(api_url, timeout=25)
        if api_raw:
            try:
                data = json.loads(api_raw.decode("utf-8", errors="replace"))
                for item in data.get("results", []):
                    book_id = item.get("id")
                    title = item.get("title", "").strip()
                    authors = ", ".join([a.get("name", "").strip() for a in item.get("authors", [])]) or "Unknown"
                    epub_url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.epub"
                    results.append({
                        "id": str(book_id),
                        "title": title,
                        "author": authors,
                        "summary": f"Project Gutenberg eBook #{book_id}",
                        "download_url": epub_url,
                        "size_bytes": 0,
                        "source": "Project Gutenberg",
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                pass

    return results[:limit]


def search_books(query, source="auto", limit=5):
    source = source.lower()
    if source in ["se", "standard_ebooks", "standardebooks"]:
        return search_standard_ebooks(query, limit=limit)
    elif source in ["pg", "gutenberg"]:
        return search_gutenberg(query, limit=limit)
    else:
        # Auto: check Standard Ebooks first for superior typography
        results = search_standard_ebooks(query, limit=limit)
        if len(results) < limit:
            remaining = limit - len(results)
            results.extend(search_gutenberg(query, limit=remaining))
        return results[:limit]


def download_epub(book_info, out_dir="./downloads/books"):
    os.makedirs(out_dir, exist_ok=True)
    title_slug = re.sub(r"[^\w\s-]", "", book_info["title"]).strip().replace(" ", "_")[:50]
    author_slug = re.sub(r"[^\w\s-]", "", book_info["author"]).strip().replace(" ", "_")[:30]
    filename = f"{author_slug}_{title_slug}.epub".strip("_")
    if not filename.endswith(".epub"):
        filename += ".epub"
    dest_path = os.path.join(out_dir, filename)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024 and zipfile.is_zipfile(dest_path):
        return dest_path, os.path.getsize(dest_path), True

    proxy = detect_proxy()
    cmd = ["curl", "-L", "-sS", "--fail", "--connect-timeout", "15", "--max-time", "120"]
    if proxy:
        cmd.extend(["--proxy", proxy])
    cmd.extend(["-o", dest_path + ".tmp", book_info["download_url"]])

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(dest_path + ".tmp") and os.path.getsize(dest_path + ".tmp") > 1024:
        if not zipfile.is_zipfile(dest_path + ".tmp"):
            if os.path.exists(dest_path + ".tmp"):
                os.remove(dest_path + ".tmp")
            raise RuntimeError("Downloaded file is not a valid EPUB zip archive (may be an HTML redirect or blocked page)")
        os.replace(dest_path + ".tmp", dest_path)
        return dest_path, os.path.getsize(dest_path), False
    else:
        if os.path.exists(dest_path + ".tmp"):
            os.remove(dest_path + ".tmp")
        err = res.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Download failed: {err}")


def format_size(bytes_num):
    if not bytes_num:
        return "Unknown"
    if bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    return f"{bytes_num / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(description="Search and download public domain books (Standard Ebooks & Project Gutenberg)")
    subparsers = parser.add_subparsers(dest="command")

    # search
    search_parser = subparsers.add_parser("search", help="Search books")
    search_parser.add_argument("query", help="Book title or author query")
    search_parser.add_argument("--source", "-s", default="auto", choices=["auto", "standard_ebooks", "gutenberg"], help="Book source (default: auto)")
    search_parser.add_argument("--limit", "-n", type=int, default=5, help="Max results (default: 5)")
    search_parser.add_argument("--json", action="store_true", help="Output JSON")

    # download
    down_parser = subparsers.add_parser("download", help="Download a book")
    down_parser.add_argument("query", help="Book title or download URL")
    down_parser.add_argument("--source", "-s", default="auto", choices=["auto", "standard_ebooks", "gutenberg"], help="Book source")
    down_parser.add_argument("--output-dir", "-o", default="./downloads/books", help="Output folder (default: ./downloads/books)")
    down_parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        results = search_books(args.query, source=args.source, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return

        print(f"\n📖 Search Results for '{args.query}' (Found: {len(results)})")
        print("─" * 65)
        if not results:
            print("  No books found. Try different keywords.")
        for idx, b in enumerate(results, 1):
            sz = f" ({format_size(b['size_bytes'])})" if b.get("size_bytes") else ""
            print(f"  [{idx}] {b['title']} — {b['author']}{sz}")
            print(f"      Source: {b['source']}")
            if b.get("summary"):
                summary_snippet = b["summary"].replace("\n", " ")[:90] + ("..." if len(b["summary"]) > 90 else "")
                print(f"      Summary: {summary_snippet}")
        print("─" * 65)

    elif args.command == "download":
        query_str = args.query.strip()
        target = None

        if query_str.startswith("http://") or query_str.startswith("https://"):
            if "standardebooks.org" in query_str:
                clean_url = query_str.split("?")[0].rstrip("/")
                slug = clean_url.split("/")[-1]
                epub_url = f"{clean_url}/downloads/{slug}_advanced.epub?source=download" if not clean_url.endswith(".epub") else query_str
                target = {
                    "id": slug,
                    "title": slug.replace("-", " ").title(),
                    "author": "Standard Ebooks",
                    "download_url": epub_url,
                    "source": "Standard Ebooks",
                }
            elif "gutenberg.org" in query_str:
                match = re.search(r"(\d+)", query_str)
                bid = match.group(1) if match else "unknown"
                target = {
                    "id": bid,
                    "title": f"Gutenberg eBook #{bid}",
                    "author": "Project Gutenberg",
                    "download_url": f"https://www.gutenberg.org/cache/epub/{bid}/pg{bid}.epub",
                    "source": "Project Gutenberg",
                }
            else:
                target = {
                    "id": "direct",
                    "title": os.path.splitext(os.path.basename(query_str.split("?")[0]))[0] or "eBook",
                    "author": "Online",
                    "download_url": query_str,
                    "source": "Direct URL",
                }
        elif query_str.isdigit():
            target = {
                "id": query_str,
                "title": f"Gutenberg eBook #{query_str}",
                "author": "Project Gutenberg",
                "download_url": f"https://www.gutenberg.org/cache/epub/{query_str}/pg{query_str}.epub",
                "source": "Project Gutenberg",
            }
        else:
            results = search_books(query_str, source=args.source, limit=1)
            if not results:
                print(f"Error: No book found matching '{query_str}'", file=sys.stderr)
                sys.exit(1)
            target = results[0]
        print(f"⬇ Downloading '{target['title']}' by {target['author']} from {target['source']} ...")
        try:
            dest_path, size_bytes, existing = download_epub(target, out_dir=args.output_dir)
            status_text = "Already downloaded" if existing else "Successfully downloaded"
            print(f"✓ {status_text}: {dest_path} ({format_size(size_bytes)})")
            if args.json:
                print(json.dumps({
                    "title": target["title"],
                    "author": target["author"],
                    "source": target["source"],
                    "path": os.path.abspath(dest_path),
                    "size_bytes": size_bytes,
                }, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"✗ Download failed: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
