#!/usr/bin/env python3
"""
WordTower Exporter for EnglishCraft
Bridges processed English corpus (EPUB, Text, YouTube transcripts) into WordTower.
"""

import sys
import os
import json
import argparse
import subprocess
import shutil

def find_wordtower_request_script():
    """Locate the official WordTower request.py script in workspace."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../wordtower/scripts/request.py")),
        os.path.abspath(os.path.join(os.getcwd(), ".agents/skills/wordtower/scripts/request.py")),
        os.path.expanduser("~/.gemini/antigravity/skills/wordtower/scripts/request.py"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def check_credentials():
    """Check if WORDTOWER_API_KEY is available."""
    token = os.environ.get("WORDTOWER_API_KEY") or os.environ.get("WORDS_API_KEY")
    if not token:
        print("\n⚠️  [WordTower Exporter] Missing WORDTOWER_API_KEY!", file=sys.stderr)
        print("   Please obtain an API key (format: wtk-...) from WordTower (https://www.wordtower.cn)", file=sys.stderr)
        print("   Then set it via: export WORDTOWER_API_KEY=wtk_your_key\n", file=sys.stderr)
        return False
    return True

def export_epub(epub_path, title=None):
    if not check_credentials():
        sys.exit(1)
    
    script_path = find_wordtower_request_script()
    if not script_path:
        print("Error: Could not locate WordTower official skill (scripts/request.py).", file=sys.stderr)
        print("Please ensure 'wordtower' skill is installed in .agents/skills/wordtower.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(epub_path):
        print(f"Error: EPUB file not found: {epub_path}", file=sys.stderr)
        sys.exit(1)

    book_title = title or os.path.splitext(os.path.basename(epub_path))[0]
    cmd = ["python3", script_path, "--epub", os.path.abspath(epub_path), "--title", book_title]
    print(f"🗼 Exporting EPUB to WordTower: '{book_title}' ...")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

def export_text(text_path, title=None):
    if not check_credentials():
        sys.exit(1)

    script_path = find_wordtower_request_script()
    if not script_path:
        print("Error: Could not locate WordTower official skill.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(text_path):
        print(f"Error: Text file not found: {text_path}", file=sys.stderr)
        sys.exit(1)

    article_title = title or os.path.splitext(os.path.basename(text_path))[0]
    cmd = ["python3", script_path, "--text", os.path.abspath(text_path), "--title", article_title]
    print(f"🗼 Exporting text to WordTower: '{article_title}' ...")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

def export_youtube(youtube_url, subtitles_path, title=None):
    if not check_credentials():
        sys.exit(1)

    script_path = find_wordtower_request_script()
    if not script_path:
        print("Error: Could not locate WordTower official skill.", file=sys.stderr)
        sys.exit(1)

    vid_title = title or "YouTube Video Lesson"
    cmd = ["python3", script_path, "--youtube", youtube_url, "--subtitles", os.path.abspath(subtitles_path), "--title", vid_title]
    print(f"🗼 Exporting YouTube course with subtitles to WordTower: '{vid_title}' ...")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

def main():
    parser = argparse.ArgumentParser(description="Export English corpus to WordTower")
    subparsers = parser.add_subparsers(dest="type")

    # epub
    epub_parser = subparsers.add_parser("epub", help="Export EPUB to WordTower")
    epub_parser.add_argument("file", help="Path to EPUB file")
    epub_parser.add_argument("--title", "-t", help="Title for WordTower course")

    # text
    text_parser = subparsers.add_parser("text", help="Export Markdown/Text to WordTower")
    text_parser.add_argument("file", help="Path to Markdown/Text file")
    text_parser.add_argument("--title", "-t", help="Title for WordTower course")

    # youtube
    yt_parser = subparsers.add_parser("youtube", help="Export YouTube video & subtitles to WordTower")
    yt_parser.add_argument("url", help="YouTube video URL")
    yt_parser.add_argument("--subtitles", "-s", required=True, help="Path to .srt / .vtt subtitles")
    yt_parser.add_argument("--title", "-t", help="Course title")

    args = parser.parse_args()
    if not args.type:
        parser.print_help()
        sys.exit(1)

    if args.type == "epub":
        export_epub(args.file, args.title)
    elif args.type == "text":
        export_text(args.file, args.title)
    elif args.type == "youtube":
        export_youtube(args.url, args.subtitles, args.title)

if __name__ == "__main__":
    main()
