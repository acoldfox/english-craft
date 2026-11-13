#!/usr/bin/env python3
"""
WordTower Exporter for EnglishCraft
Bridges processed English corpus (EPUB, Text, YouTube transcripts) into WordTower (v0.7.0).
Implements the complete official 3-step protocol:
  1. Preview (/imports/epub/preview, /imports/preview, or /imports/youtube/preview)
  2. Submit  (/imports/epub or /imports/text with preview_id + idempotency_key)
  3. Poll    (/imports/status until succeeded/failed/cancelled or timeout)
"""

import sys
import os
import re
import json
import time
import uuid
import tempfile
import argparse
import subprocess
from pathlib import Path


def find_wordtower_request_script():
    """Locate the official WordTower request.py script in workspace or user skills."""
    override = os.environ.get("WORDTOWER_REQUEST_SCRIPT")
    if override:
        path = os.path.abspath(os.path.expanduser(override))
        if not os.path.isfile(path):
            raise RuntimeError("WORDTOWER_REQUEST_SCRIPT does not point to a file")
        return path
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../wordtower/scripts/request.py")),
        os.path.abspath(os.path.join(os.getcwd(), ".agents/skills/wordtower/scripts/request.py")),
    ]
    for root in ("~/.agents/skills", "~/.codex/skills", "~/.claude/skills",
                 "~/.gemini/config/skills", "~/.gemini/antigravity/skills",
                 "~/.workbuddy/skills", ".workbuddy/skills"):
        candidates.append(os.path.expanduser(root + "/wordtower/scripts/request.py"))
    for candidate in candidates:
        if os.path.isfile(candidate):
            # Older installations support only text import and legacy credentials.
            source = Path(candidate).read_text(encoding="utf-8")
            if "--subtitles" in source and "WORDTOWER_API_KEY" in source:
                return candidate
    return None


def prepare_env():
    """Validate WORDTOWER_API_KEY (or bridge WORDS_API_KEY) and return sub-process env."""
    env = os.environ.copy()
    if not env.get("WORDTOWER_API_KEY"):
        for env_path in [".env", os.path.expanduser("~/.env")]:
            if os.path.exists(env_path):
                try:
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("WORDTOWER_API_KEY="):
                                env["WORDTOWER_API_KEY"] = line.split("=", 1)[1].strip().strip('"\'')
                            elif line.startswith("NO_PROXY=") or line.startswith("no_proxy="):
                                env["NO_PROXY"] = line.split("=", 1)[1].strip().strip('"\'')
                                env["no_proxy"] = env["NO_PROXY"]
                except Exception:
                    pass
    token = env.get("WORDTOWER_API_KEY") or env.get("WORDS_API_KEY") or ""
    if not token:
        print("\n⚠️  [WordTower Exporter] Missing WORDTOWER_API_KEY!", file=sys.stderr)
        print("   1. Go to WordTower (https://www.wordtower.cn) -> Account -> Skill & Token", file=sys.stderr)
        print("   2. Create a token (format: wtk- followed by 24 characters)", file=sys.stderr)
        print("   3. Configure it via: export WORDTOWER_API_KEY=wtk-xxxxxxxxxxxxxxxxxxxxxxxx\n", file=sys.stderr)
        return None
    if not re.fullmatch(r"wtk-[A-Za-z0-9_-]{24}", token):
        print(
            "\n⚠️  [WordTower Exporter] Invalid WORDTOWER_API_KEY format!",
            file=sys.stderr,
        )
        print("   Official token must match: wtk-<24 alphanumeric/_/- characters>\n", file=sys.stderr)
        return None
    env["WORDTOWER_API_KEY"] = token
    return env


def run_request_json(script_path, payload_dict, env):
    """Execute wordtower request.py with a temporary JSON request file and return parsed JSON."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as tf:
        json.dump(payload_dict, tf, ensure_ascii=False)
        temp_path = tf.name
    try:
        res = subprocess.run(
            ["python3", script_path, temp_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if res.returncode != 0:
            err_msg = (res.stdout or res.stderr).strip()
            raise RuntimeError(f"WordTower request failed:\n{err_msg}")
        return json.loads(res.stdout)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def submit_and_poll(script_path, preview_resp, submit_api, env, preview_only=False, max_wait=120):
    """Handle preview inspection, submission with idempotency_key, and job polling."""
    data = preview_resp.get("data", {})
    preview_id = data.get("preview_id")
    title = data.get("title", "Untitled")
    norm_chars = data.get("normalized_chars", 0)
    chapters = data.get("chapter_count") or data.get("chapters")
    subtitles = data.get("subtitle_count")

    print(f"✓ Preview generated (preview_id: {preview_id})")
    print(f"  Title: {title} | Normalized Chars: {norm_chars:,}", end="")
    if chapters:
        print(f" | Chapters: {chapters}", end="")
    if subtitles:
        print(f" | Subtitles: {subtitles}", end="")
    print()

    if preview_only:
        print(json.dumps(preview_resp, ensure_ascii=False, indent=2))
        return

    if not preview_id:
        raise RuntimeError(f"No preview_id returned from WordTower:\n{json.dumps(preview_resp, ensure_ascii=False, indent=2)}")

    idempotency_key = str(uuid.uuid4())
    print(f"🚀 Submitting import task ({submit_api}, idempotency_key: {idempotency_key}) ...")
    submit_resp = run_request_json(
        script_path,
        {
            "api_name": submit_api,
            "preview_id": preview_id,
            "idempotency_key": idempotency_key,
        },
        env,
    )
    submit_data = submit_resp.get("data", {})
    job_id = submit_data.get("job_id")
    if not job_id:
        print(json.dumps(submit_resp, ensure_ascii=False, indent=2))
        return

    print(f"⏳ Job accepted (job_id: {job_id}). Polling status ...")
    start_time = time.time()
    poll_interval = int(submit_data.get("poll_after_seconds") or 3)

    while time.time() - start_time < max_wait:
        time.sleep(max(1, min(poll_interval, 15)))
        status_resp = run_request_json(
            script_path,
            {"api_name": "/imports/status", "job_id": job_id},
            env,
        )
        s_data = status_resp.get("data", {})
        status = s_data.get("status", "unknown")
        poll_interval = int(s_data.get("poll_after_seconds") or 4)

        if status == "succeeded":
            print(f"\n🎉 Course import succeeded! (job_id: {job_id})")
            if s_data.get("completed_chapters") is not None:
                print(f"   Completed Chapters: {s_data.get('completed_chapters')}")
            if s_data.get("billed_chars") is not None:
                print(f"   Billed Chars:       {s_data.get('billed_chars'):,}")
            if s_data.get("reader_link"):
                print(f"   Reader Link:        {s_data.get('reader_link')}")
            return
        elif status in ("failed", "cancelled"):
            print(f"\n✗ Import {status} (job_id: {job_id}):", file=sys.stderr)
            print(json.dumps(status_resp, ensure_ascii=False, indent=2), file=sys.stderr)
            sys.exit(1)
        else:
            print(f"   Status: {status} ...")

    print(f"\nℹ️  Job {job_id} is still processing on WordTower. You can check its status later with job_id: {job_id}")


def get_required_request_script():
    """Ensure WordTower request script is located with clear user-friendly instructions."""
    script_path = find_wordtower_request_script()
    if not script_path:
        print("\n⚠️  [WordTower Exporter] Could not locate WordTower official skill (scripts/request.py).", file=sys.stderr)
        print("   WordTower export is an optional downstream integration.", file=sys.stderr)
        print("   To enable it, download the official skill package from https://www.wordtower.cn (Account -> Skill & Token)", file=sys.stderr)
        print("   and place it in .agents/skills/wordtower (or set WORDTOWER_REQUEST_SCRIPT=/path/to/request.py).\n", file=sys.stderr)
        sys.exit(1)
    return script_path


def export_epub(epub_path, title=None, preview_only=False):
    env = prepare_env()
    if not env:
        sys.exit(1)

    script_path = get_required_request_script()

    if not os.path.exists(epub_path):
        print(f"Error: EPUB file not found: {epub_path}", file=sys.stderr)
        sys.exit(1)

    book_title = title or os.path.splitext(os.path.basename(epub_path))[0]
    cmd = ["python3", script_path, "--epub", os.path.abspath(epub_path), "--title", book_title]
    print(f"🗼 Uploading & previewing EPUB on WordTower: '{book_title}' ...")
    res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(res.stdout or res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

    preview_resp = json.loads(res.stdout)
    submit_and_poll(script_path, preview_resp, "/imports/epub", env, preview_only=preview_only)


def export_text(text_path, title=None, preview_only=False):
    env = prepare_env()
    if not env:
        sys.exit(1)

    script_path = get_required_request_script()

    if not os.path.exists(text_path):
        print(f"Error: Text file not found: {text_path}", file=sys.stderr)
        sys.exit(1)

    content = Path(text_path).read_text(encoding="utf-8-sig")
    if Path(text_path).suffix.lower() in {".srt", ".vtt"} or re.search(
        r"^\s*\d{2}:\d{2}.*-->", content, re.MULTILINE
    ):
        raise ValueError("Timed/video transcripts must use youtube URL --subtitles FILE; text import cannot retain playback timing")

    article_title = title or os.path.splitext(os.path.basename(text_path))[0]
    cmd = ["python3", script_path, "--text", os.path.abspath(text_path), "--title", article_title]
    print(f"🗼 Previewing text on WordTower: '{article_title}' ...")
    res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(res.stdout or res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

    preview_resp = json.loads(res.stdout)
    submit_and_poll(script_path, preview_resp, "/imports/text", env, preview_only=preview_only)


def validate_youtube_preview(response, youtube_url):
    """Never submit a plain-text preview as a synchronized video course."""
    data = response.get("data") or {}
    count = data.get("subtitle_count")
    if (data.get("media_type") != "youtube" or data.get("source_url") != youtube_url
            or not isinstance(count, int) or isinstance(count, bool) or count <= 0
            or not data.get("preview_id")):
        raise RuntimeError("YouTube preview lacks a verified subtitle timeline; import stopped. "
                           "Use timed SRT/VTT/JSON and update the official WordTower skill/server. "
                           "Do not fall back to text import.")
    print(f"✓ Verified YouTube sentence timeline: {count} timed cues")


def export_youtube(youtube_url, subtitles_path, title=None, preview_only=False):
    env = prepare_env()
    if not env:
        sys.exit(1)

    script_path = get_required_request_script()

    if not os.path.exists(subtitles_path):
        print(f"Error: Subtitles file not found: {subtitles_path}", file=sys.stderr)
        sys.exit(1)

    vid_title = title or os.path.splitext(os.path.basename(subtitles_path))[0] or "YouTube Video Lesson"
    cmd = [
        "python3",
        script_path,
        "--youtube",
        youtube_url,
        "--subtitles",
        os.path.abspath(subtitles_path),
        "--title",
        vid_title,
    ]
    print(f"🗼 Previewing YouTube course with subtitles on WordTower: '{vid_title}' ...")
    res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(res.stdout or res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

    preview_resp = json.loads(res.stdout)
    validate_youtube_preview(preview_resp, youtube_url)
    submit_and_poll(script_path, preview_resp, "/imports/text", env, preview_only=preview_only)


def main():
    parser = argparse.ArgumentParser(description="Export English corpus to WordTower (Preview -> Submit -> Poll)")
    subparsers = parser.add_subparsers(dest="type")

    # epub
    epub_parser = subparsers.add_parser("epub", help="Export EPUB to WordTower")
    epub_parser.add_argument("file", help="Path to EPUB file")
    epub_parser.add_argument("--title", "-t", help="Title for WordTower course")
    epub_parser.add_argument("--preview-only", action="store_true", help="Only generate preview without submitting")

    # text
    text_parser = subparsers.add_parser("text", help="Export Markdown/Text to WordTower")
    text_parser.add_argument("file", help="Path to Markdown/Text file")
    text_parser.add_argument("--title", "-t", help="Title for WordTower course")
    text_parser.add_argument("--preview-only", action="store_true", help="Only generate preview without submitting")

    # youtube
    yt_parser = subparsers.add_parser("youtube", help="Export YouTube video & subtitles to WordTower")
    yt_parser.add_argument("url", help="YouTube video URL")
    yt_parser.add_argument("--subtitles", "-s", required=True, help="Path to .srt / .vtt / .json subtitles")
    yt_parser.add_argument("--title", "-t", help="Course title")
    yt_parser.add_argument("--preview-only", action="store_true", help="Only generate preview without submitting")

    args = parser.parse_args()
    if not args.type:
        parser.print_help()
        sys.exit(1)

    if args.type == "epub":
        export_epub(args.file, args.title, preview_only=args.preview_only)
    elif args.type == "text":
        export_text(args.file, args.title, preview_only=args.preview_only)
    elif args.type == "youtube":
        export_youtube(args.url, args.subtitles, args.title, preview_only=args.preview_only)


if __name__ == "__main__":
    main()
