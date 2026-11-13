#!/usr/bin/env python3
"""
Podcast Search & Zero-Local-ASR Transcript Extractor for EnglishCraft
Searches English podcasts via Apple iTunes API (zero-key), lists episodes with covers
and durations, and retrieves transcripts without local Whisper/ASR using a 3-tier pipeline:
  Tier 1: RSS <podcast:transcript> tag (when feed is accessible & provides transcript)
  Tier 2: YouTube Equivalent Match via fetch_youtube.py / yt-dlp (.srt + Markdown)
  Tier 3: Episode Show Notes / Description fallback
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fetch_youtube import download_subtitles, get_ytdlp_command  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def format_duration(seconds: float | int | None) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds is None:
        return "--:--"
    total_sec = int(seconds)
    if total_sec <= 0:
        return "--:--"
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Sanitize a string into a safe filename stem."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned.strip("._")
    return (cleaned[:max_len] or "podcast_transcript").strip("._")


def _http_get_bytes(url: str, timeout: int = 12) -> bytes:
    """Perform HTTP GET with User-Agent and gzip decompression."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return raw


def http_get_json(url: str, timeout: int = 12) -> dict[str, Any]:
    """Perform HTTP GET and parse JSON response."""
    raw = _http_get_bytes(url, timeout=timeout)
    return json.loads(raw.decode("utf-8", errors="replace"))


def search_podcasts(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search podcasts on Apple iTunes Search API."""
    encoded = urllib.parse.quote(query.strip())
    url = f"https://itunes.apple.com/search?media=podcast&entity=podcast&term={encoded}&limit={limit}"
    data = http_get_json(url)
    results = []
    for idx, item in enumerate(data.get("results", []) or [], start=1):
        results.append({
            "index": idx,
            "collection_id": item.get("collectionId"),
            "name": item.get("collectionName") or item.get("trackName") or "Untitled Podcast",
            "artist": item.get("artistName") or "Unknown",
            "genre": item.get("primaryGenreName") or "",
            "episode_count": item.get("trackCount") or 0,
            "feed_url": item.get("feedUrl") or "",
            "cover": item.get("artworkUrl600") or item.get("artworkUrl100") or "",
            "apple_url": item.get("collectionViewUrl") or "",
        })
    return results


def fetch_episodes(podcast_query_or_id: str, limit: int = 10) -> dict[str, Any]:
    """Resolve podcast and fetch its recent episodes via Apple iTunes Lookup API."""
    raw_target = podcast_query_or_id.strip()
    podcast_meta: dict[str, Any] = {}

    if raw_target.isdigit():
        collection_id = int(raw_target)
    else:
        matches = search_podcasts(raw_target, limit=1)
        if not matches:
            raise ValueError(f"No podcast found matching '{podcast_query_or_id}'")
        podcast_meta = matches[0]
        collection_id = int(podcast_meta["collection_id"])

    url = (
        f"https://itunes.apple.com/lookup?id={collection_id}"
        f"&media=podcast&entity=podcastEpisode&limit={limit}"
    )
    data = http_get_json(url, timeout=15)
    raw_results = data.get("results", []) or []
    if not raw_results:
        raise ValueError(f"No lookup data returned for podcast id {collection_id}")

    header = raw_results[0]
    podcast_info = {
        "collection_id": header.get("collectionId") or collection_id,
        "name": header.get("collectionName") or podcast_meta.get("name") or raw_target,
        "artist": header.get("artistName") or podcast_meta.get("artist") or "Unknown",
        "genre": header.get("primaryGenreName") or podcast_meta.get("genre") or "",
        "feed_url": header.get("feedUrl") or podcast_meta.get("feed_url") or "",
        "cover": header.get("artworkUrl600") or header.get("artworkUrl100") or podcast_meta.get("cover") or "",
        "apple_url": header.get("collectionViewUrl") or podcast_meta.get("apple_url") or "",
    }

    episodes = []
    for idx, ep in enumerate(raw_results[1:], start=1):
        dur_ms = ep.get("trackTimeMillis")
        dur_sec = int(dur_ms // 1000) if isinstance(dur_ms, (int, float)) and dur_ms > 0 else None
        rel_date = (ep.get("releaseDate") or "")[:10]
        episodes.append({
            "index": idx,
            "track_id": ep.get("trackId"),
            "title": ep.get("trackName") or "Untitled Episode",
            "date": rel_date,
            "duration_seconds": dur_sec,
            "duration": format_duration(dur_sec),
            "audio_url": ep.get("episodeUrl") or "",
            "cover": ep.get("artworkUrl160") or ep.get("artworkUrl600") or podcast_info["cover"],
            "description": (ep.get("description") or ep.get("shortDescription") or "").strip(),
            "episode_guid": ep.get("episodeGuid") or "",
            "apple_url": ep.get("trackViewUrl") or "",
        })

    return {
        "podcast": podcast_info,
        "total_results": len(episodes),
        "episodes": episodes,
    }


def check_rss_transcript(
    feed_url: str,
    episode_title: str,
    episode_guid: str | None = None,
) -> tuple[str, str] | None:
    """
    Attempt Tier 1: Fetch RSS XML and check for Podcasting 2.0 <podcast:transcript> tag.
    Wrapped defensively so large/incomplete RSS feeds never fail the pipeline.
    """
    if not feed_url:
        return None
    try:
        raw = _http_get_bytes(feed_url, timeout=10)
        root = ET.fromstring(raw)
    except Exception:
        return None

    channel = root.find("channel")
    if channel is None:
        return None

    target_title = episode_title.strip().lower()
    for item in channel.findall("item"):
        item_guid = (item.findtext("guid") or "").strip()
        item_title = (item.findtext("title") or "").strip().lower()

        matched = False
        if episode_guid and item_guid and episode_guid == item_guid:
            matched = True
        elif target_title and item_title == target_title:
            matched = True

        if not matched:
            continue

        for el in item:
            if el.tag.endswith("transcript"):
                t_url = el.attrib.get("url")
                t_type = (el.attrib.get("type") or "").lower()
                if not t_url:
                    continue
                try:
                    content = _http_get_bytes(t_url, timeout=10).decode("utf-8", errors="replace")
                    ext = "srt" if "srt" in t_type or t_url.lower().endswith(".srt") else (
                        "vtt" if "vtt" in t_type or t_url.lower().endswith(".vtt") else "txt"
                    )
                    if content.strip():
                        return content, ext
                except Exception:
                    continue
    return None


def _score_yt_candidate(entry: dict[str, Any], episode_title: str, duration_sec: int | None) -> float:
    """Score YouTube search entry by title token overlap and duration proximity."""
    entry_title = (entry.get("title") or "").lower()
    ep_tokens = set(re.findall(r"[a-z0-9]+", episode_title.lower()))
    yt_tokens = set(re.findall(r"[a-z0-9]+", entry_title))
    overlap = len(ep_tokens & yt_tokens) / max(1, len(ep_tokens))

    score = overlap * 100.0
    yt_dur = entry.get("duration")
    if duration_sec and isinstance(yt_dur, (int, float)) and yt_dur > 0:
        diff_ratio = abs(yt_dur - duration_sec) / max(1, duration_sec)
        score -= min(diff_ratio * 40.0, 40.0)
    return score


def match_youtube_subtitle(
    podcast_name: str,
    episode_title: str,
    output_dir: Path,
    duration_sec: int | None = None,
    proxy: str | None = None,
) -> tuple[Path, dict[str, Any]] | None:
    """
    Attempt Tier 2: Match podcast episode on YouTube via yt-dlp ytsearch5
    and download its English timed .srt subtitle.
    """
    ytdlp_cmd = get_ytdlp_command()
    query = f"ytsearch5:{podcast_name} {episode_title}"
    cmd = (
        ytdlp_cmd
        + [
            "--flat-playlist",
            "--no-warnings",
            "--no-update",
            "-J",
            query,
        ]
    )
    if proxy:
        cmd.extend(["--proxy", proxy])

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        data = json.loads(res.stdout)
    except Exception:
        return None

    candidates = [
        e for e in (data.get("entries") or [])
        if isinstance(e, dict) and e.get("id")
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda e: _score_yt_candidate(e, episode_title, duration_sec),
        reverse=True,
    )

    for cand in candidates[:3]:
        vid_id = cand["id"]
        try:
            srt_path = download_subtitles(vid_id, output_dir=output_dir, proxy=proxy)
            vid_url = cand.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
            matched_info = {
                "id": vid_id,
                "title": cand.get("title") or episode_title,
                "url": vid_url,
                "channel": cand.get("channel") or cand.get("uploader") or "",
                "duration": cand.get("duration"),
            }
            return srt_path, matched_info
        except Exception:
            continue

    return None


def srt_to_markdown(srt_path: Path, meta: dict[str, Any]) -> str:
    """
    Convert an SRT/VTT subtitle file into a clean, paragraph-segmented Markdown
    reading sheet with header metadata.
    """
    raw = srt_path.read_text(encoding="utf-8-sig", errors="replace")
    clean_lines: list[str] = []
    prev_line = ""

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.isdigit() or "-->" in stripped or stripped.startswith("WEBVTT"):
            continue
        if stripped.startswith(("Kind:", "Language:")):
            continue
        text = re.sub(r"<[^>]+>", "", stripped)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        # Deduplicate rolling auto-caption lines
        if text == prev_line:
            continue
        clean_lines.append(text)
        prev_line = text

    full_text = " ".join(clean_lines)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    sentences = re.split(r"(?<=[.!?])\s+", full_text) if full_text else []
    paragraphs: list[str] = []
    chunk: list[str] = []
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        chunk.append(s)
        if len(chunk) >= 5:
            paragraphs.append(" ".join(chunk))
            chunk = []
    if chunk:
        paragraphs.append(" ".join(chunk))

    body = "\n\n".join(paragraphs) if paragraphs else full_text

    lines = [
        f"# {meta.get('episode_title', 'Podcast Transcript')}",
        "",
        f"- **Podcast**: {meta.get('podcast_name', 'Unknown')}",
        f"- **Published**: {meta.get('date', 'Unknown')}",
        f"- **Duration**: {meta.get('duration', '--:--')}",
    ]
    if meta.get("audio_url"):
        lines.append(f"- **Audio**: {meta['audio_url']}")
    if meta.get("youtube_url"):
        lines.append(f"- **YouTube Source**: {meta['youtube_url']}")
    lines.extend(["", "---", "", body, ""])
    return "\n".join(lines)


def _format_shownotes_markdown(meta: dict[str, Any], description: str) -> str:
    """Format Tier 3 fallback Show Notes into a clean Markdown document."""
    clean_desc = re.sub(r"<[^>]+>", "\n", description)
    clean_desc = html.unescape(clean_desc)
    clean_desc = re.sub(r"\n{3,}", "\n\n", clean_desc).strip()

    lines = [
        f"# {meta.get('episode_title', 'Podcast Episode')}",
        "",
        f"- **Podcast**: {meta.get('podcast_name', 'Unknown')}",
        f"- **Published**: {meta.get('date', 'Unknown')}",
        f"- **Duration**: {meta.get('duration', '--:--')}",
    ]
    if meta.get("audio_url"):
        lines.append(f"- **Audio**: {meta['audio_url']}")
    lines.extend([
        "",
        "> Note: No RSS transcript or YouTube subtitle match was available; showing episode Show Notes.",
        "",
        "---",
        "",
        clean_desc or "(No description available.)",
        "",
    ])
    return "\n".join(lines)


def extract_episode_transcript(
    podcast_query_or_id: str,
    index: int = 1,
    episode_keyword: str | None = None,
    output_dir: str | Path = "./transcripts",
    proxy: str | None = None,
) -> dict[str, Any]:
    """
    Extract transcript for a podcast episode via the 3-tier zero-local-ASR pipeline:
      1. RSS <podcast:transcript>
      2. YouTube Equivalent Match (.srt + .md)
      3. Show Notes fallback (.md)
    """
    fetch_limit = max(index, 20 if episode_keyword else index)
    ep_data = fetch_episodes(podcast_query_or_id, limit=fetch_limit)
    podcast = ep_data["podcast"]
    episodes = ep_data["episodes"]
    if not episodes:
        raise ValueError(f"No episodes found for '{podcast['name']}'")

    selected = None
    if episode_keyword:
        kw = episode_keyword.strip().lower()
        for ep in episodes:
            if kw in ep["title"].lower():
                selected = ep
                break
        if selected is None:
            raise ValueError(f"No episode title matching keyword '{episode_keyword}' in '{podcast['name']}'")
    else:
        if index < 1 or index > len(episodes):
            raise ValueError(f"Episode index {index} out of range (1..{len(episodes)})")
        selected = episodes[index - 1]

    out_folder = Path(output_dir).resolve()
    out_folder.mkdir(parents=True, exist_ok=True)
    stem = sanitize_filename(f"{podcast['name']}_{selected['title']}")
    md_path = out_folder / f"{stem}.md"

    meta = {
        "podcast_name": podcast["name"],
        "episode_title": selected["title"],
        "date": selected["date"],
        "duration": selected["duration"],
        "audio_url": selected["audio_url"],
        "youtube_url": None,
    }

    # Tier 1: RSS <podcast:transcript>
    rss_res = check_rss_transcript(
        podcast.get("feed_url", ""),
        selected["title"],
        selected.get("episode_guid"),
    )
    if rss_res is not None:
        raw_content, ext = rss_res
        srt_path: Path | None = None
        if ext in ("srt", "vtt"):
            srt_path = out_folder / f"{stem}.{ext}"
            srt_path.write_text(raw_content, encoding="utf-8")
            md_content = srt_to_markdown(srt_path, meta)
        else:
            md_content = _format_shownotes_markdown(meta, raw_content).replace(
                "No RSS transcript or YouTube subtitle match was available; showing episode Show Notes.",
                "Extracted directly from official RSS <podcast:transcript>.",
            )
        md_path.write_text(md_content, encoding="utf-8")
        return {
            "status": "success",
            "source_tier": "rss_transcript",
            "podcast_name": podcast["name"],
            "episode_title": selected["title"],
            "date": selected["date"],
            "duration": selected["duration"],
            "audio_url": selected["audio_url"],
            "youtube_url": None,
            "srt_path": str(srt_path) if srt_path else None,
            "markdown_path": str(md_path),
        }

    # Tier 2: YouTube Equivalent Match
    yt_res = match_youtube_subtitle(
        podcast["name"],
        selected["title"],
        output_dir=out_folder,
        duration_sec=selected.get("duration_seconds"),
        proxy=proxy,
    )
    if yt_res is not None:
        srt_path, yt_info = yt_res
        meta["youtube_url"] = yt_info["url"]
        md_content = srt_to_markdown(srt_path, meta)
        md_path.write_text(md_content, encoding="utf-8")
        return {
            "status": "success",
            "source_tier": "youtube_subtitle",
            "podcast_name": podcast["name"],
            "episode_title": selected["title"],
            "date": selected["date"],
            "duration": selected["duration"],
            "audio_url": selected["audio_url"],
            "youtube_url": yt_info["url"],
            "youtube_title": yt_info["title"],
            "srt_path": str(srt_path),
            "markdown_path": str(md_path),
        }

    # Tier 3: Show Notes Fallback
    md_content = _format_shownotes_markdown(meta, selected.get("description", ""))
    md_path.write_text(md_content, encoding="utf-8")
    return {
        "status": "fallback",
        "source_tier": "shownotes_fallback",
        "podcast_name": podcast["name"],
        "episode_title": selected["title"],
        "date": selected["date"],
        "duration": selected["duration"],
        "audio_url": selected["audio_url"],
        "youtube_url": None,
        "srt_path": None,
        "markdown_path": str(md_path),
    }


def print_search_human(results: list[dict[str, Any]]):
    print(f"\n🎙️  Found {len(results)} podcasts:\n")
    for item in results:
        print(f"  [{item['index']:2d}] {item['name']}  ({item['artist']})")
        print(f"       ID: {item['collection_id']} | Genre: {item['genre']} | Episodes: {item['episode_count']}")
        if item["apple_url"]:
            print(f"       🔗 {item['apple_url']}")
        print()


def print_search_markdown(results: list[dict[str, Any]]):
    print("\n### 🎙️ 播客检索结果\n")
    print("| # | 封面 | 播客名称 | 制作方 | 集数 | ID / 链接 |")
    print("|:---:|:---:|:---|:---|:---:|:---|")
    for item in results:
        cover = item["cover"]
        img_md = f'<img src="{cover}" width="64" style="border-radius:6px;" />' if cover else "-"
        name = item["name"].replace("|", "\\|")
        artist = item["artist"].replace("|", "\\|")
        link = f"[{item['collection_id']}]({item['apple_url']})" if item["apple_url"] else str(item["collection_id"])
        print(f"| **{item['index']}** | {img_md} | **{name}** | {artist} | {item['episode_count']} | {link} |")
    print()


def print_episodes_human(ep_data: dict[str, Any]):
    pod = ep_data["podcast"]
    episodes = ep_data["episodes"]
    print(f"\n🎙️  Podcast: {pod['name']} ({pod['artist']})")
    print(f"🔗  Apple URL: {pod.get('apple_url')}")
    print(f"📊  Latest {len(episodes)} episodes:\n")
    for ep in episodes:
        print(f"  [{ep['index']:2d}] ⏱️ [{ep['duration']}] ({ep['date']})  {ep['title']}")
        if ep["audio_url"]:
            print(f"       🎧 {ep['audio_url']}")
        print()


def print_episodes_markdown(ep_data: dict[str, Any]):
    pod = ep_data["podcast"]
    episodes = ep_data["episodes"]
    cover = pod.get("cover")
    cover_md = f'<img src="{cover}" width="64" style="border-radius:6px;" /> ' if cover else ""
    print(f"\n### {cover_md}🎙️ [{pod['name']}]({pod.get('apple_url', '')}) — {pod['artist']}\n")
    print("| # | 单集标题 | 时长 | 发布日期 | 音频直链 |")
    print("|:---:|:---|:---:|:---:|:---:|")
    for ep in episodes:
        title = ep["title"].replace("|", "\\|")
        audio = f"[MP3]({ep['audio_url']})" if ep["audio_url"] else "-"
        print(f"| **{ep['index']}** | {title} | `{ep['duration']}` | {ep['date']} | {audio} |")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Search podcasts, list episodes, and extract transcripts without local ASR."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # search
    search_p = subparsers.add_parser("search", help="Search podcasts via Apple iTunes")
    search_p.add_argument("query", help="Podcast search keyword")
    search_p.add_argument("-n", "--limit", type=int, default=5, help="Max results (default: 5)")
    search_p.add_argument("--markdown", action="store_true", help="Output Markdown table with covers")
    search_p.add_argument("--json", action="store_true", help="Output JSON")

    # episodes
    ep_p = subparsers.add_parser("episodes", help="List recent episodes of a podcast")
    ep_p.add_argument("podcast", help="Podcast name or iTunes collection ID")
    ep_p.add_argument("-n", "--limit", type=int, default=10, help="Number of episodes (default: 10)")
    ep_p.add_argument("--markdown", action="store_true", help="Output Markdown table with cover")
    ep_p.add_argument("--json", action="store_true", help="Output JSON")

    # transcript
    tr_p = subparsers.add_parser("transcript", help="Extract episode transcript (zero local ASR)")
    tr_p.add_argument("podcast", help="Podcast name or iTunes collection ID")
    tr_p.add_argument("-i", "--index", type=int, default=1, help="Episode index (default: 1)")
    tr_p.add_argument("-e", "--episode", help="Match episode title by keyword instead of index")
    tr_p.add_argument("-o", "--output-dir", default="./transcripts", help="Output directory")
    tr_p.add_argument("--proxy", help="HTTP/HTTPS proxy for yt-dlp")
    tr_p.add_argument("--json", action="store_true", help="Output JSON")

    if len(sys.argv) > 1 and sys.argv[1] == "wordtower":
        print(
            "❌ WordTower does not support direct podcast audio/RSS import.\n"
            "   Use 'transcript' to extract the .md / .srt first, then export via exporters/wordtower.py (youtube or text) if needed.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Default subcommand to 'episodes' if omitted
    if len(sys.argv) > 1 and sys.argv[1] not in ("search", "episodes", "transcript", "-h", "--help"):
        sys.argv.insert(1, "episodes")

    args = parser.parse_args()

    try:
        if args.subcommand == "search":
            results = search_podcasts(args.query, limit=args.limit)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            elif args.markdown:
                print_search_markdown(results)
            else:
                print_search_human(results)

        elif args.subcommand == "episodes":
            ep_data = fetch_episodes(args.podcast, limit=args.limit)
            if args.json:
                print(json.dumps(ep_data, ensure_ascii=False, indent=2))
            elif args.markdown:
                print_episodes_markdown(ep_data)
            else:
                print_episodes_human(ep_data)

        elif args.subcommand == "transcript":
            res = extract_episode_transcript(
                args.podcast,
                index=args.index,
                episode_keyword=args.episode,
                output_dir=args.output_dir,
                proxy=args.proxy,
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"\n✅ Episode: {res['episode_title']}")
                print(f"📡 Source Tier: {res['source_tier']}")
                if res.get("audio_url"):
                    print(f"🎧 Audio MP3: {res['audio_url']}")
                if res.get("youtube_url"):
                    print(f"📺 YouTube Match: {res['youtube_url']}")
                if res.get("srt_path"):
                    print(f"⏱️  SRT Subtitles: {res['srt_path']}")
                print(f"📄 Markdown Transcript: {res['markdown_path']}\n")
        else:
            parser.print_help()
    except Exception as exc:
        print(f"\n❌ [EnglishCraft Podcast] Error: {exc}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
