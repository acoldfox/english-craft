#!/usr/bin/env python3
"""
YouTube Channel & Video Extractor for EnglishCraft
Leverages yt-dlp to fetch YouTube video lists from channels, handles, playlists, or search queries.
Provides video metadata (title, duration, URL, cover image) and supports subtitle extraction
for direct integration into WordTower (词塔) and vocab curation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def find_ytdlp() -> str:
    """Find yt-dlp executable path or raise helpful error."""
    override = os.environ.get("YTDLP_PATH")
    if override and os.path.isfile(override) and os.access(override, os.X_OK):
        return override

    found = shutil.which("yt-dlp")
    if found:
        return found

    common_paths = [
        "/opt/homebrew/bin/yt-dlp",
        "/usr/local/bin/yt-dlp",
        os.path.expanduser("~/.local/bin/yt-dlp"),
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    print(
        "\n❌ [EnglishCraft YouTube] Error: 'yt-dlp' is not installed or not in PATH.\n"
        "   Please install yt-dlp first:\n"
        "     - macOS:  brew install yt-dlp\n"
        "     - Python: pip install -U yt-dlp\n",
        file=sys.stderr,
    )
    sys.exit(1)


def format_duration(seconds: float | int | None) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds is None:
        return "--:--"
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def normalize_youtube_target(target: str) -> str:
    """
    Normalize user input into a valid yt-dlp target.
    Supports:
      - @username, @handle -> https://www.youtube.com/@handle/videos
      - username (without @) -> https://www.youtube.com/@username/videos
      - https://www.youtube.com/@handle -> append /videos
      - https://www.youtube.com/channel/UC... -> append /videos
      - https://www.youtube.com/playlist?list=...
      - https://www.youtube.com/watch?v=...
    """
    raw = target.strip()

    if raw.startswith("http://") or raw.startswith("https://"):
        if "youtube.com/@" in raw and not raw.endswith("/videos"):
            return raw.rstrip("/") + "/videos"
        if "youtube.com/channel/UC" in raw and not raw.endswith("/videos"):
            return raw.rstrip("/") + "/videos"
        return raw

    if raw.startswith("UC") and len(raw) == 24:
        return f"https://www.youtube.com/channel/{raw}/videos"

    handle = raw if raw.startswith("@") else f"@{raw}"
    return f"https://www.youtube.com/{handle}/videos"


def fetch_channel_videos(
    target: str,
    limit: int = 10,
    start: int = 1,
    proxy: str | None = None,
) -> dict[str, Any]:
    """Fetch video entries from a YouTube channel/playlist using yt-dlp."""
    ytdlp = find_ytdlp()
    url = normalize_youtube_target(target)

    end = start + limit - 1
    cmd = [
        ytdlp,
        "--flat-playlist",
        "--no-warnings",
        "--no-update",
        "--playlist-start",
        str(start),
        "--playlist-end",
        str(end),
        "-J",
        url,
    ]

    if proxy:
        cmd.extend(["--proxy", proxy])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.strip() or exc.stdout.strip()
        print(f"❌ yt-dlp failed to fetch {url}:\n{err_msg}", file=sys.stderr)
        raise RuntimeError(f"Failed to fetch videos from {url}") from exc

    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("yt-dlp returned invalid JSON output") from exc

    channel_name = data.get("channel") or data.get("uploader") or target
    channel_url = data.get("channel_url") or data.get("uploader_url") or url
    followers = data.get("channel_follower_count")

    entries = []
    current_idx = start
    for entry in data.get("entries", []) or []:
        if not entry or not isinstance(entry, dict):
            continue
        vid_id = entry.get("id")
        if not vid_id:
            continue
        title = entry.get("title") or "Untitled Video"
        duration_sec = entry.get("duration")
        duration_str = format_duration(duration_sec)
        vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"

        thumbnails = entry.get("thumbnails") or []
        cover_url = ""
        if thumbnails and isinstance(thumbnails, list):
            valid_thumbs = [t for t in thumbnails if isinstance(t, dict) and t.get("url")]
            if valid_thumbs:
                cover_url = valid_thumbs[-1].get("url", "")

        entries.append({
            "index": current_idx,
            "id": vid_id,
            "title": title,
            "duration_seconds": duration_sec,
            "duration": duration_str,
            "url": vid_url,
            "cover": cover_url,
            "view_count": entry.get("view_count"),
        })
        current_idx += 1

    return {
        "channel_name": channel_name,
        "channel_url": channel_url,
        "followers": followers,
        "target_url": url,
        "total_results": len(entries),
        "entries": entries,
    }


def download_subtitles(
    video_url_or_id: str,
    output_dir: str | Path | None = None,
    lang: str = "en,en-US,en-GB",
    proxy: str | None = None,
) -> Path:
    """Download English subtitles for a video and return the .srt path."""
    ytdlp = find_ytdlp()

    if video_url_or_id.startswith("http://") or video_url_or_id.startswith("https://"):
        vid_url = video_url_or_id
        vid_id = re.search(r"[?&]v=([^&]+)", vid_url)
        safe_id = vid_id.group(1) if vid_id else "youtube_sub"
    else:
        safe_id = video_url_or_id.strip()
        vid_url = f"https://www.youtube.com/watch?v={safe_id}"

    out_folder = Path(output_dir or "./transcripts").resolve()
    out_folder.mkdir(parents=True, exist_ok=True)
    out_template = str(out_folder / f"{safe_id}.%(ext)s")

    cmd = [
        ytdlp,
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang",
        lang,
        "--sub-format",
        "srt",
        "--skip-download",
        "--no-warnings",
        "--no-update",
        "-o",
        out_template,
        vid_url,
    ]

    if proxy:
        cmd.extend(["--proxy", proxy])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip()
        raise RuntimeError(f"Failed to download subtitles: {err}")

    srt_candidates = list(out_folder.glob(f"{safe_id}*.srt"))
    if not srt_candidates:
        raise FileNotFoundError(f"No subtitle file was generated in {out_folder}")

    # Prefer direct exact language match if available
    srt_candidates.sort(key=lambda p: len(p.name))
    return srt_candidates[0]


def print_human_table(result: dict[str, Any], show_covers: bool = False):
    """Print results in a clean terminal list."""
    ch_name = result.get("channel_name", "YouTube Channel")
    followers = result.get("followers")
    follower_str = f" ({followers:,} subscribers)" if followers else ""
    entries = result.get("entries", [])

    print(f"\n📺  Channel: {ch_name}{follower_str}")
    print(f"🔗  URL: {result.get('target_url')}")
    print(f"📊  Showing {len(entries)} videos:\n")

    for item in entries:
        idx = item["index"]
        dur = item["duration"]
        title = item["title"]
        url = item["url"]
        cover = item["cover"]

        print(f"  [{idx:2d}] ⏱️ [{dur}]  {title}")
        print(f"       🔗 {url}")
        if show_covers and cover:
            print(f"       🖼️  Cover: {cover}")
        print()


def print_markdown(result: dict[str, Any]):
    """Print results in rich Markdown format with image thumbnails and links."""
    ch_name = result.get("channel_name", "YouTube Channel")
    followers = result.get("followers")
    follower_str = f" ({followers:,} subscribers)" if followers else ""
    entries = result.get("entries", [])

    print(f"\n### 📺 [{ch_name}]({result.get('target_url')}){follower_str}\n")
    print("| # | 封面 | 视频标题 | 时长 | 链接 |")
    print("|:---:|:---:|:---|:---:|:---:|")

    for item in entries:
        idx = item["index"]
        dur = item["duration"]
        title = item["title"].replace("|", "\\|")
        url = item["url"]
        cover = item["cover"]
        img_md = f'<img src="{cover}" width="120" style="border-radius:4px;" />' if cover else "-"
        print(f"| **{idx}** | {img_md} | [{title}]({url}) | `{dur}` | [观看]({url}) |")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube channel video lists, download subtitles, or import to WordTower."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List videos for a YouTube channel or handle")
    list_parser.add_argument("target", help="YouTube handle (e.g. @TEDEd), username, or channel URL")
    list_parser.add_argument("-n", "--limit", type=int, default=10, help="Number of videos to list (default: 10)")
    list_parser.add_argument("-s", "--start", type=int, default=1, help="Starting video index (default: 1)")
    list_parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    list_parser.add_argument("--markdown", action="store_true", help="Output results in rich Markdown format")
    list_parser.add_argument("--show-covers", action="store_true", help="Display image cover URLs in terminal")
    list_parser.add_argument("--proxy", help="HTTP/HTTPS proxy (e.g. http://127.0.0.1:7890)")

    # subtitles subcommand
    sub_parser = subparsers.add_parser("subtitles", help="Download subtitles for a YouTube video")
    sub_parser.add_argument("video", help="YouTube video URL or Video ID")
    sub_parser.add_argument("-o", "--output-dir", default="./transcripts", help="Directory to save .srt file")
    sub_parser.add_argument("--lang", default="en", help="Subtitle language (default: en)")
    sub_parser.add_argument("--proxy", help="HTTP/HTTPS proxy")
    sub_parser.add_argument("--json", action="store_true", help="Output result as JSON")

    # wordtower subcommand
    wt_parser = subparsers.add_parser("wordtower", help="Download subtitles and import video into WordTower")
    wt_parser.add_argument("video", help="YouTube video URL or Video ID")
    wt_parser.add_argument("-t", "--title", help="Course title for WordTower (defaults to video title)")
    wt_parser.add_argument("--preview-only", action="store_true", help="Preview only on WordTower without submit")
    wt_parser.add_argument("--proxy", help="HTTP/HTTPS proxy")

    # Support shorthand if no subcommand given: 'fetch_youtube.py @TEDEd'
    args = None
    if len(sys.argv) > 1 and sys.argv[1] not in ("list", "subtitles", "wordtower", "-h", "--help"):
        # Synthesize 'list' command
        sys.argv.insert(1, "list")

    args = parser.parse_args()

    if args.subcommand == "list":
        result = fetch_channel_videos(
            target=args.target,
            limit=args.limit,
            start=args.start,
            proxy=args.proxy,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.markdown:
            print_markdown(result)
        else:
            print_human_table(result, show_covers=args.show_covers)

    elif args.subcommand == "subtitles":
        try:
            srt_path = download_subtitles(
                video_url_or_id=args.video,
                output_dir=args.output_dir,
                lang=args.lang,
                proxy=args.proxy,
            )
            if args.json:
                print(json.dumps({
                    "status": "success",
                    "video": args.video,
                    "subtitles_path": str(srt_path),
                }, indent=2))
            else:
                print(f"\n✅ Subtitles saved to: {srt_path}\n")
        except Exception as exc:
            print(f"\n❌ Error downloading subtitles: {exc}\n", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "wordtower":
        # First download subtitle
        try:
            print(f"📥 Downloading subtitles for {args.video} ...")
            srt_path = download_subtitles(args.video, proxy=args.proxy)
            print(f"✓ Subtitles downloaded: {srt_path}")
        except Exception as exc:
            print(f"❌ Failed to download subtitles: {exc}", file=sys.stderr)
            sys.exit(1)

        # Call exporters/wordtower.py
        exporter_script = Path(__file__).resolve().parent / "exporters" / "wordtower.py"
        if not exporter_script.is_file():
            print(f"❌ exporters/wordtower.py not found at {exporter_script}", file=sys.stderr)
            sys.exit(1)

        vid_url = args.video if args.video.startswith("http") else f"https://www.youtube.com/watch?v={args.video}"
        cmd = [
            sys.executable,
            str(exporter_script),
            "youtube",
            vid_url,
            "--subtitles",
            str(srt_path),
        ]
        if args.title:
            cmd.extend(["--title", args.title])
        if args.preview_only:
            cmd.append("--preview-only")

        print("🗼 Launching WordTower import pipeline...")
        subprocess.run(cmd, check=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
