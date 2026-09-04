import os
import shutil
import tempfile
from urllib.parse import urlparse

import requests

from app.services import storage_service


class AudioFetchError(Exception):
    pass


def download_from_url(url: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="islah-audio-url-")
    filename = os.path.basename(urlparse(url).path) or "audio"
    path = os.path.join(tmp_dir, filename)
    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return path
    except requests.exceptions.RequestException as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise AudioFetchError(str(exc)) from exc


def download_from_s3(key: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="islah-audio-s3-")
    path = os.path.join(tmp_dir, os.path.basename(key))
    data = storage_service.get_bytes(key)
    with open(path, "wb") as f:
        f.write(data)
    return path


def get_local_path(doc: dict) -> str:
    if doc["source"] == "upload":
        if not doc.get("s3_key"):
            raise AudioFetchError("Audio has no stored file")
        return download_from_s3(doc["s3_key"])
    if doc["source"] == "url":
        if not doc.get("source_url"):
            raise AudioFetchError("Audio has no source URL")
        return download_from_url(doc["source_url"])
    raise AudioFetchError(f"Unknown audio source: {doc['source']}")


def cleanup(path: str) -> None:
    shutil.rmtree(os.path.dirname(path), ignore_errors=True)
