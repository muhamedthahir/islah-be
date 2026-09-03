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
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
    }
    cookie_file = _resolve_cookie_file(tmp_dir)
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise AudioDownloadError(str(exc)) from exc


def cleanup_audio(file_path: str) -> None:
    shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
