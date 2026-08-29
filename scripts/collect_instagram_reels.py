#!/usr/bin/env python3
"""
Collect every Reel URL from a public Instagram profile into a SQL-ready JSONL manifest.

Designed for local execution on a machine where the user is already logged into Instagram.
It NEVER asks for or prints an Instagram password/cookie. Prefer an Instaloader session file.

Public GitHub safety rule:
- Do not commit full third-party transcripts/captions by default.
- The manifest keeps URL, metadata, short excerpt, hashes, status, and local transcript path.
- Full ASR text is written only to --private-dir when --scan-audio is enabled.

Requirements:
    python3 -m pip install --upgrade instaloader
Optional ASR:
    python3 -m pip install faster-whisper
    brew install ffmpeg   # macOS, recommended

First-time authenticated session (run locally; password remains with Instaloader):
    instaloader --login YOUR_IG_USERNAME
Then:
    python3 scripts/collect_instagram_reels.py \
      --username hedge.sphere.ai \
      --login-user YOUR_IG_USERNAME \
      --scan-audio
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import instaloader
except ImportError:
    sys.exit("Missing dependency: pip install --upgrade instaloader")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_excerpt(text: str, limit: int = 20) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    words = text.split(" ")
    return " ".join(words[:limit])


def safe_caption_fields(caption: str | None) -> dict:
    caption = (caption or "").strip()
    return {
        "caption_excerpt": word_excerpt(caption, 20),
        "caption_sha256": sha256_text(caption) if caption else None,
        "caption_char_count": len(caption),
    }


def download_video(url: str, dst: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=90) as r, dst.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def transcribe_audio(video_path: Path, model_name: str, language: str | None) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "ASR requested but faster-whisper is missing. "
            "Install with: python3 -m pip install faster-whisper"
        )

    model = WhisperModel(model_name, device="auto", compute_type="auto")
    segments, _info = model.transcribe(
        str(video_path),
        language=language,
        vad_filter=True,
    )
    return "\n".join(seg.text.strip() for seg in segments if seg.text.strip())


def build_loader(login_user: str | None, sessionfile: str | None):
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=False,
    )

    if login_user:
        try:
            if sessionfile:
                L.load_session_from_file(login_user, filename=sessionfile)
            else:
                L.load_session_from_file(login_user)
            print(f"[auth] Loaded Instaloader session for @{login_user}", file=sys.stderr)
        except Exception as e:
            sys.exit(
                f"Could not load Instagram session for @{login_user}: {e}\n"
                f"Create it locally first with:\n"
                f"  instaloader --login {login_user}\n"
                f"Do NOT send the session file/cookies/password to anyone."
            )
    else:
        print(
            "[auth] Anonymous mode. Instagram may rate-limit or require login. "
            "For a complete inventory, use --login-user with a local session.",
            file=sys.stderr,
        )
    return L


def post_to_record(post, username: str) -> dict:
    caption_fields = safe_caption_fields(getattr(post, "caption", None))
    date_utc = getattr(post, "date_utc", None)
    if date_utc is not None:
        date_utc = date_utc.replace(tzinfo=timezone.utc).isoformat()

    record = {
        "account": username,
        "platform": "instagram",
        "media_type": "reel",
        "shortcode": post.shortcode,
        "reel_url": f"https://www.instagram.com/reel/{post.shortcode}/",
        "published_at_utc": date_utc,
        "owner_username": getattr(post, "owner_username", username),
        "video_duration_seconds": getattr(post, "video_duration", None),
        "video_view_count": getattr(post, "video_view_count", None),
        "likes": getattr(post, "likes", None),
        "comments": getattr(post, "comments", None),
        "is_video": getattr(post, "is_video", True),
        **caption_fields,
        "transcript_status": "not_scanned",
        "transcript_local_path": None,
        "transcript_sha256": None,
        "transcript_word_count": None,
        "subtitle_excerpt": None,
        "ocr_status": "not_scanned",
        "skill_extraction_status": "pending",
        "collection_status": "enumerated",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default="hedge.sphere.ai")
    ap.add_argument("--login-user", help="Your own IG username; loads an existing Instaloader session.")
    ap.add_argument("--sessionfile", help="Optional explicit Instaloader session file path.")
    ap.add_argument("--out", default="hedge_sphere_reels_manifest.jsonl")
    ap.add_argument("--private-dir", default=".private_instagram_transcripts")
    ap.add_argument(
        "--scan-audio",
        action="store_true",
        help="Download each Reel temporarily and run local faster-whisper ASR.",
    )
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument(
        "--language",
        default="zh",
        help="Whisper language code. Use 'auto' for auto-detect.",
    )
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    private_dir = Path(args.private_dir).expanduser()
    if args.scan_audio:
        private_dir.mkdir(parents=True, exist_ok=True)

    L = build_loader(args.login_user, args.sessionfile)

    try:
        profile = instaloader.Profile.from_username(L.context, args.username)
        reels = profile.get_reels()
    except Exception as e:
        sys.exit(
            f"Failed to open @{args.username} Reels: {e}\n"
            "Instagram is likely requiring login/rate-limiting this request. "
            "Use a local authenticated Instaloader session."
        )

    seen = set()
    count = 0
    asr_ok = 0
    asr_fail = 0

    with out.open("w", encoding="utf-8") as f:
        for post in reels:
            if post.shortcode in seen:
                continue
            seen.add(post.shortcode)
            rec = post_to_record(post, args.username)

            if args.scan_audio:
                tmp_path = None
                try:
                    video_url = post.video_url
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                    download_video(video_url, tmp_path)

                    language = None if args.language == "auto" else args.language
                    transcript = transcribe_audio(tmp_path, args.whisper_model, language)

                    transcript_path = private_dir / f"{post.shortcode}.txt"
                    transcript_path.write_text(transcript, encoding="utf-8")

                    rec["transcript_status"] = "scanned_private"
                    rec["transcript_local_path"] = str(transcript_path)
                    rec["transcript_sha256"] = sha256_text(transcript)
                    rec["transcript_word_count"] = len(re.sub(r"\s+", " ", transcript).split())
                    rec["subtitle_excerpt"] = word_excerpt(transcript, 20)
                    asr_ok += 1
                except Exception as e:
                    rec["transcript_status"] = "scan_failed"
                    rec["transcript_error"] = str(e)
                    asr_fail += 1
                finally:
                    if tmp_path and tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except OSError:
                            pass

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
            print(
                f"[{count:04d}] {rec['reel_url']}  {rec['transcript_status']}",
                file=sys.stderr,
            )

    print("\nDONE", file=sys.stderr)
    print(f"Reels: {count}", file=sys.stderr)
    print(f"Manifest: {out}", file=sys.stderr)
    if args.scan_audio:
        print(f"ASR success: {asr_ok} / failed: {asr_fail}", file=sys.stderr)
        print(f"Private transcripts: {private_dir}", file=sys.stderr)
        print("Do NOT commit that private transcript directory to a public repo.", file=sys.stderr)


if __name__ == "__main__":
    main()
