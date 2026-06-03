"""Busca de imagens de produtos em uma pasta do Google Drive."""

from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List

import requests

from .cache import cached
from .local_catalog import IMG_EXTENSIONS
from .product_media import _classify_variant, _match_filename


GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _parse_folder_id(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None

    folder_match = re.search(r"/folders/([A-Za-z0-9_-]+)", cleaned)
    if folder_match:
        return folder_match.group(1)

    query_match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", cleaned)
    if query_match:
        return query_match.group(1)

    return cleaned


def is_configured() -> bool:
    return bool(
        _parse_folder_id(_optional_env("CATALOG_GOOGLE_DRIVE_FOLDER_ID"))
        and _optional_env("CATALOG_GOOGLE_DRIVE_API_KEY")
    )


def _build_file_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=view&id={file_id}"


def _is_image_file(item: Dict) -> bool:
    mime_type = str(item.get("mimeType") or "")
    if mime_type.startswith("image/"):
        return True
    name = str(item.get("name") or "").lower()
    return any(name.endswith(ext) for ext in IMG_EXTENSIONS)


def _matches_code(name: str, code: str) -> bool:
    if _match_filename(name, code) is not None:
        return True
    return re.search(rf"(?<!\d){re.escape(str(code))}(?!\d)", name or "") is not None


def _image_sort_key(item: Dict, code: str) -> tuple:
    name = str(item.get("name") or "")
    variant = _match_filename(name, code)
    if variant is None:
        variant = 99
    return (variant, name.lower())


def _request_children(folder_id: str, api_key: str | None) -> Iterable[Dict]:
    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        if api_key:
            params["key"] = api_key

        response = requests.get(GOOGLE_DRIVE_FILES_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("files") or []:
            if isinstance(item, dict):
                yield item

        page_token = payload.get("nextPageToken")
        if not page_token:
            break


@cached
def list_google_drive_images(folder_id: str | None = None, max_depth: int | None = None) -> List[Dict]:
    root_folder_id = _parse_folder_id(folder_id or _optional_env("CATALOG_GOOGLE_DRIVE_FOLDER_ID"))
    if not root_folder_id:
        return []

    api_key = _optional_env("CATALOG_GOOGLE_DRIVE_API_KEY")
    if not api_key:
        raise ValueError("missing CATALOG_GOOGLE_DRIVE_API_KEY configuration")

    recursive = _parse_bool_env("CATALOG_GOOGLE_DRIVE_RECURSIVE", default=True)
    depth_limit = max_depth
    if depth_limit is None:
        depth_limit = int(os.getenv("CATALOG_GOOGLE_DRIVE_MAX_DEPTH", "4"))

    images: List[Dict] = []
    pending: list[tuple[str, int]] = [(root_folder_id, 0)]
    visited: set[str] = set()

    while pending:
        current_folder_id, depth = pending.pop(0)
        if current_folder_id in visited:
            continue
        visited.add(current_folder_id)

        for item in _request_children(current_folder_id, api_key):
            mime_type = str(item.get("mimeType") or "")
            if mime_type == GOOGLE_DRIVE_FOLDER_MIME:
                if recursive and depth < depth_limit:
                    child_id = str(item.get("id") or "").strip()
                    if child_id:
                        pending.append((child_id, depth + 1))
                continue

            if _is_image_file(item):
                file_id = str(item.get("id") or "").strip()
                if not file_id:
                    continue
                images.append(
                    {
                        "id": file_id,
                        "name": str(item.get("name") or ""),
                        "mimeType": mime_type,
                        "url": _build_file_url(file_id),
                    }
                )

    return images


def find_images_for_code(code: str, folder_id: str | None = None) -> List[Dict]:
    code_text = str(code or "").strip()
    if not code_text:
        return []

    matches = [
        item
        for item in list_google_drive_images(folder_id=folder_id)
        if _matches_code(str(item.get("name") or ""), code_text)
    ]
    matches.sort(key=lambda item: _image_sort_key(item, code_text))

    return [
        {
            "name": str(item.get("name") or ""),
            "variant": _match_filename(str(item.get("name") or ""), code_text) or 0,
            "url": str(item.get("url") or ""),
        }
        for item in matches
    ]


def categorize_photos_for_code(code: str, folder_id: str | None = None) -> Dict[str, str | None]:
    photos: Dict[str, str | None] = {
        "white_background": None,
        "ambient": None,
        "measures": None,
    }

    for image in find_images_for_code(code, folder_id=folder_id):
        variant = _classify_variant(str(image.get("name") or ""), code)
        if variant in photos and not photos[variant]:
            photos[variant] = str(image.get("url") or "") or None

    return photos
