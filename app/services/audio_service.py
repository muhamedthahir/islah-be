import os
import shutil
import tempfile

import yt_dlp

from app.config import settings


class AudioDownloadError(Exception):
    pass


def _resolve_cookie_file(tmp_dir: str) -> str | None:
    if settings.youtube_cookies_file:
        return settings.youtube_cookies_file
    if settings.youtube_cookies_content:
        path = os.path.join(tmp_dir, "cookies.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(settings.youtube_cookies_content)
        return path
    return None


def download_audio(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmp_dir = tempfile.mkdtemp(prefix="islah-audio-")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        "js_runtimes": {"node": {}},
        "extractor_args": {"youtube": {"player_client": ["android", "tv", "web"]}},
    }
    cookie_file = _resolve_cookie_file(tmp_dir)
    if cookie_file:
        exists = os.path.isfile(cookie_file)
        size = os.path.getsize(cookie_file) if exists else -1
        print(f"[audio_service] cookie_file={cookie_file} exists={exists} size={size}")
        ydl_opts["cookiefile"] = cookie_file
    else:
        print("[audio_service] no cookie file resolved")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise AudioDownloadError(str(exc)) from exc


def cleanup_audio(file_path: str) -> None:
    shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
