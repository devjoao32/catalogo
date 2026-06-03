"""Descoberta e indexacao do catalogo local de produtos."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable, Dict, List

from .product_media import (
    _canonical_category,
    _classify_variant,
    _local_file_sort_key,
    _pick_distinct_fallback,
)


IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
INDEX_EXTENSIONS = IMG_EXTENSIONS + (".lnk",)
SEGMENT_PREFIX_CODE_PATTERN = re.compile(r"^\s*(?P<code>\d{3,8})(?=\D|$)")
GENERIC_CODE_PATTERN = re.compile(r"\b(?P<code>\d{4,8})\b")
CATEGORY_STOP_TOKENS = {"C", "COM"}
CATEGORY_TRIM_TAIL_TOKENS = {"C", "COM", "DE", "DA", "DO", "DOS", "DAS", "E"}


def _env_flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _local_products_paths(base_dir: str) -> List[str]:
    return [
        os.path.join(base_dir, "TI 1", "catalogo"),
        os.path.join(base_dir, "FOTOS_PRODUTOS"),
        os.path.join(base_dir, "MARKETING", "01_PRODUTOS", "BACKUP PRODUTOS"),
        os.path.join(base_dir, "MARKETING", "Catalogo"),
        os.path.join(base_dir, "MARKETING", "01_PRODUTOS"),
    ]


def _candidate_local_roots() -> List[str]:
    candidates: List[str] = []
    explicit = os.getenv("CATALOG_LOCAL_PRODUCTS_PATH")
    if explicit:
        candidates.append(explicit)

    include_home_fallback = _env_flag("CATALOG_LOCAL_PRODUCTS_HOME_FALLBACK", default=True)
    for base_env in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "USERPROFILE"):
        base = os.getenv(base_env)
        if not base:
            continue
        base = base.rstrip("\\/")
        if base_env == "USERPROFILE":
            one_drive_base = os.path.join(base, "OneDrive")
            candidates.extend(_local_products_paths(one_drive_base))
        else:
            candidates.extend(_local_products_paths(base))

    home = str(Path.home())
    if include_home_fallback and home:
        candidates.extend(_local_products_paths(os.path.join(home, "OneDrive")))
    return candidates


def existing_local_roots(path_override: str | None = None) -> List[str]:
    roots: List[str] = []
    seen = set()
    candidates = [path_override] if path_override else _candidate_local_roots()
    for candidate in candidates:
        if not candidate:
            continue
        abs_candidate = os.path.abspath(candidate)
        norm_key = abs_candidate.lower()
        if norm_key in seen:
            continue
        if os.path.isdir(abs_candidate):
            roots.append(abs_candidate)
            seen.add(norm_key)
    return roots


def resolve_local_products_root(path_override: str | None = None) -> str | None:
    roots = existing_local_roots(path_override)
    return roots[0] if roots else None


def _clean_product_name(candidate: str) -> str:
    cleaned = re.sub(r"\s+", " ", (candidate or "").strip(" -_"))
    cleaned = re.sub(r"\s*\(\d{1,3}\)\s*$", "", cleaned)
    cleaned = re.sub(r"\s*-\s*(atalho|shortcut)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" -_")
    if not cleaned:
        return ""
    if re.fullmatch(r"[1-4]", cleaned):
        return ""
    if re.fullmatch(r"\d+", cleaned):
        return ""
    return cleaned


def _derive_category_from_product_name(product_name: str) -> str:
    cleaned = _clean_product_name(product_name)
    if not cleaned:
        return "Sem categoria"

    tokens = cleaned.split()
    category_tokens: List[str] = []
    for token in tokens:
        token_upper = token.upper()
        if any(char.isdigit() for char in token):
            break
        if token_upper in CATEGORY_STOP_TOKENS and len(category_tokens) >= 2:
            break
        category_tokens.append(token)
        if len(category_tokens) >= 4:
            break

    while category_tokens and category_tokens[-1].upper() in CATEGORY_TRIM_TAIL_TOKENS:
        category_tokens.pop()

    if not category_tokens:
        category_tokens = tokens[:2]

    category = " ".join(category_tokens).strip(" -_")
    return category or "Sem categoria"


def _extract_code_and_name_from_segment(segment: str) -> tuple[str | None, str]:
    pref = SEGMENT_PREFIX_CODE_PATTERN.search(segment or "")
    if not pref:
        return None, ""

    code = pref.group("code")
    remainder = (segment[pref.end() :] if segment else "").strip()
    remainder = re.sub(r"^[\s\-_]+", "", remainder)
    return code, _clean_product_name(remainder)


def _extract_code_from_parts(parts: List[str]) -> tuple[str | None, str, str]:
    raw_category = parts[0].strip() if len(parts) > 1 else ""
    if raw_category and not SEGMENT_PREFIX_CODE_PATTERN.search(raw_category):
        category = raw_category
    else:
        category = "Sem categoria"

    filename_stem = Path(parts[-1]).stem if parts else ""
    ordered_segments = [filename_stem]
    ordered_segments.extend(reversed(parts[:-1]))

    for segment in ordered_segments:
        code, product_name = _extract_code_and_name_from_segment(segment)
        if code:
            resolved_category = category
            if resolved_category == "Sem categoria" and product_name:
                resolved_category = _derive_category_from_product_name(product_name)
            resolved_category = _canonical_category(resolved_category, product_name)
            return code, product_name or f"Produto {code}", resolved_category

    for segment in ordered_segments:
        generic = GENERIC_CODE_PATTERN.search(segment)
        if generic:
            code = generic.group("code")
            return code, f"Produto {code}", _canonical_category(category, segment)

    return None, "", _canonical_category(category, "")


def _rel_path_in_allowed_roots(abs_path: str, roots: List[str]) -> str | None:
    if not abs_path:
        return None
    candidate = os.path.abspath(abs_path)
    if not os.path.isfile(candidate):
        return None
    for root in roots:
        root_abs = os.path.abspath(root)
        try:
            within_root = os.path.commonpath([root_abs, candidate]) == root_abs
        except ValueError:
            continue
        if within_root:
            return os.path.relpath(candidate, root_abs)
    return None


def resolve_shortcut_targets(scan_root: str) -> Dict[str, str]:
    """Resolve arquivos .lnk em scan_root para caminhos absolutos de destino."""
    if os.name != "nt":
        return {}
    if not scan_root or not os.path.isdir(scan_root):
        return {}

    safe_root = scan_root.replace("'", "''")
    script = (
        f"$root = '{safe_root}'; "
        "$shell = New-Object -ComObject WScript.Shell; "
        "Get-ChildItem -Path $root -Recurse -File -Filter *.lnk | ForEach-Object { "
        "  $target = ''; "
        "  try { $target = $shell.CreateShortcut($_.FullName).TargetPath } catch {} "
        "  [PSCustomObject]@{ link = $_.FullName; target = $target } "
        "} | ConvertTo-Json -Compress"
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except Exception:
        return {}

    if result.returncode != 0:
        return {}

    payload = (result.stdout or "").strip()
    if not payload:
        return {}

    try:
        decoded = json.loads(payload)
    except Exception:
        return {}

    rows = decoded if isinstance(decoded, list) else [decoded]
    mapping: Dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        link = str(row.get("link") or "")
        target = str(row.get("target") or "")
        if link and target:
            mapping[os.path.abspath(link)] = os.path.abspath(target)
    return mapping


def scan_local_photo_index(
    root: str,
    allowed_roots: List[str] | None = None,
    shortcut_targets: Dict[str, str] | None = None,
) -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}
    root_abs = os.path.abspath(root)
    normalized_roots = [os.path.abspath(item) for item in (allowed_roots or existing_local_roots())]
    if root_abs not in normalized_roots:
        normalized_roots = [root_abs, *normalized_roots]
    shortcut_targets = shortcut_targets or {}

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            lowered_name = filename.lower()
            if not lowered_name.endswith(INDEX_EXTENSIONS):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root)
            parts = rel_path.split(os.sep)
            code, product_name, category = _extract_code_from_parts(parts)
            if not code:
                continue

            record = index.setdefault(
                code,
                {
                    "code": code,
                    "name": product_name or f"Produto {code}",
                    "category": category or "Sem categoria",
                    "files": [],
                    "variants": {"white_background": None, "ambient": None, "measures": None},
                },
            )
            if product_name and record["name"].startswith("Produto "):
                record["name"] = product_name
            if category and record["category"] == "Sem categoria":
                record["category"] = category

            if lowered_name.endswith(IMG_EXTENSIONS):
                file_info = {"name": filename, "full_path": full_path, "rel_path": rel_path}
                record["files"].append(file_info)
                variant = _classify_variant(filename, code)
                if variant in record["variants"] and record["variants"][variant] is None:
                    record["variants"][variant] = file_info
                continue

            target_path = shortcut_targets.get(os.path.abspath(full_path))
            target_ext = os.path.splitext(target_path or "")[1].lower()
            if target_ext not in IMG_EXTENSIONS:
                continue
            target_rel_path = _rel_path_in_allowed_roots(target_path, normalized_roots)
            if not target_rel_path:
                continue

            link_name = filename[:-4] if filename.lower().endswith(".lnk") else filename
            file_info = {
                "name": link_name,
                "full_path": target_path,
                "rel_path": target_rel_path,
            }
            record["files"].append(file_info)
            variant = _classify_variant(link_name, code)
            if variant in record["variants"] and record["variants"][variant] is None:
                record["variants"][variant] = file_info

    for record in index.values():
        record["files"].sort(key=lambda item: _local_file_sort_key(item, record.get("code", "")))
        explicitly_assigned = {
            item["rel_path"]
            for item in record["variants"].values()
            if item and item.get("rel_path")
        }
        chosen = set()

        white = record["variants"]["white_background"]
        if white is None and record["files"]:
            white = record["files"][0]
            record["variants"]["white_background"] = white
        if white:
            chosen.add(white["rel_path"])

        ambient = record["variants"]["ambient"]
        if ambient:
            chosen.add(ambient["rel_path"])
        else:
            fallback_pool = [
                item for item in record["files"]
                if item.get("rel_path") not in explicitly_assigned
            ]
            fallback = _pick_distinct_fallback(fallback_pool, chosen)
            if fallback:
                record["variants"]["ambient"] = fallback
                chosen.add(fallback["rel_path"])

        measures = record["variants"]["measures"]
        if not measures:
            fallback_pool = [
                item for item in record["files"]
                if item.get("rel_path") not in explicitly_assigned
            ]
            fallback = _pick_distinct_fallback(fallback_pool, chosen)
            if fallback:
                record["variants"]["measures"] = fallback

    return index


def build_local_photo_index(
    root_path: str | None = None,
    resolve_root: Callable[[str | None], str | None] = resolve_local_products_root,
    existing_roots_resolver: Callable[[str | None], List[str]] = existing_local_roots,
    shortcut_target_resolver: Callable[[str], Dict[str, str]] = resolve_shortcut_targets,
) -> Dict[str, Dict]:
    root = resolve_root(root_path)
    if not root:
        return {}
    return scan_local_photo_index(
        root,
        allowed_roots=existing_roots_resolver(None),
        shortcut_targets=shortcut_target_resolver(os.path.abspath(root)),
    )


def get_local_index(
    path_override: str | None = None,
    existing_roots_resolver: Callable[[str | None], List[str]] = existing_local_roots,
    shortcut_target_resolver: Callable[[str], Dict[str, str]] = resolve_shortcut_targets,
) -> Dict[str, Dict]:
    roots = existing_roots_resolver(path_override)
    if not roots:
        return {}

    for root in roots:
        rebuilt = scan_local_photo_index(
            root,
            allowed_roots=existing_roots_resolver(None),
            shortcut_targets=shortcut_target_resolver(os.path.abspath(root)),
        )
        if rebuilt:
            return rebuilt
    return {}
