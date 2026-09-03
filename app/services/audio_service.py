import os
import shutil
import tempfile

import yt_dlp

from app.config import settings


class AudioDownloadError(Exception):
    pass


def download_audio(video_id: str) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmp_dir = tempfile.mkdtemp(prefix="islah-audio-")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
    }
    if settings.youtube_cookies_file:
        ydl_opts["cookiefile"] = settings.youtube_cookies_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise AudioDownloadError(str(exc)) from exc


def cleanup_audio(file_path: str) -> None:
    shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
