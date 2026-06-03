"""Utilitarios compartilhados para classificacao e ordenacao de midia de produtos."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List
import unicodedata
from urllib.parse import quote


SEGMENT_PREFIX_CODE_PATTERN = re.compile(r"^\s*(?P<code>\d{3,8})(?=\D|$)")
PARENTHESIZED_VARIANT_SUFFIX_PATTERN = re.compile(r"\((?P<variant>\d{1,3})\)\s*$")
LEGACY_NUMERIC_VARIANT_PATTERN = re.compile(r"^[-_]\s*(?P<variant>\d{1,3})\s*$")


def _match_filename(name: str, code: str):
    stem = Path(name or "").stem.strip()
    pref = SEGMENT_PREFIX_CODE_PATTERN.match(stem)
    if not pref:
        return None
    if pref.group("code") != str(code):
        return None
    remainder = stem[pref.end() :].strip()
    if not remainder:
        return 0

    legacy_variant = LEGACY_NUMERIC_VARIANT_PATTERN.match(remainder)
    if legacy_variant:
        return int(legacy_variant.group("variant"))

    parenthesized_variant = PARENTHESIZED_VARIANT_SUFFIX_PATTERN.search(remainder)
    if parenthesized_variant:
        return int(parenthesized_variant.group("variant"))

    return 0


def _classify_variant(name: str, code: str = "") -> str:
    if code:
        numeric_variant = _match_filename(name, str(code))
        if numeric_variant == 1:
            return "white_background"
        if numeric_variant == 2:
            return "measures"
        if numeric_variant == 3:
            return "ambient"

    lowered = name.lower()
    if "branco" in lowered or "white" in lowered:
        return "white_background"
    if "ambient" in lowered or "ambiente" in lowered or "cena" in lowered:
        return "ambient"
    if "medida" in lowered or "measure" in lowered or "dimens" in lowered:
        return "measures"
    return "other"


def _normalize_name_for_match(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name or "")
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_accents.lower()


def _token_to_category(token: str, next_token: str = "") -> str | None:
    token = (token or "").upper()
    next_token = (next_token or "").upper()
    if not token:
        return None

    if token in {"ARANDELA", "ARANDELAS", "ARANDEDA"} or token.startswith("ARANDEL"):
        return "ARANDELA"
    if token.startswith("ABAJUR"):
        return "ABAJUR"
    if token.startswith("PENDENTE"):
        return "PENDENTE"
    if token.startswith("LUSTRE"):
        return "LUSTRE"
    if token.startswith("PAINEL"):
        return "PAINEL"
    if token.startswith("PLAFON"):
        return "PLAFON"
    if token in {"MINI"} and next_token.startswith("TRILHO"):
        return "TRILHO"
    if token.startswith("TRILHO"):
        return "TRILHO"
    if token.startswith("PERFIL"):
        return "PERFIL"
    if token.startswith("SENSOR"):
        return "SENSOR"
    if token.startswith("BOCAL"):
        return "BOCAL"
    if token.startswith("ESPETO"):
        return "ESPETO"
    if token.startswith("BALIZADOR"):
        return "BALIZADOR"
    if token.startswith("ESPELHO"):
        return "ESPELHO"
    if token.startswith("RELE"):
        return "RELE"
    if token.startswith("REFLET") or token.startswith("HOLOFOTE"):
        return "REFLETOR"
    if token.startswith("LAMP"):
        return "LAMPADA"
    if token.startswith("DRIVER") or token == "DRIVE" or token.startswith("FONTE"):
        return "DRIVER/FONTE"
    if token == "FITA":
        return "FITA LED"
    if token.startswith("LUMINARIA") or token in {"LUMI", "LUM", "LUMIN"}:
        return "LUMINARIA"
    return None


def _normalized_tokens(text: str) -> List[str]:
    normalized = _normalize_name_for_match(text).upper()
    normalized = re.sub(r"[^A-Z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.split() if normalized else []


def _canonical_category(category: str, product_name: str = "") -> str:
    candidates = [category, product_name]
    for candidate in candidates:
        tokens = _normalized_tokens(candidate)
        if not tokens:
            continue

        if "ILUMINACAO" in tokens and "PUBLICA" in tokens:
            return "ILUMINACAO PUBLICA"
        if "PUBLICA" in tokens and ("LUM" in tokens or "LUMIN" in tokens):
            return "ILUMINACAO PUBLICA"

        first = _token_to_category(tokens[0], tokens[1] if len(tokens) > 1 else "")
        if first:
            return first

        for idx, token in enumerate(tokens[1:], start=1):
            mapped = _token_to_category(token, tokens[idx + 1] if idx + 1 < len(tokens) else "")
            if mapped and mapped != "LUMINARIA":
                return mapped

        if any(
            _token_to_category(token, tokens[idx + 1] if idx + 1 < len(tokens) else "")
            == "LUMINARIA"
            for idx, token in enumerate(tokens)
        ):
            return "LUMINARIA"

        if "FITA" in tokens and "LED" in tokens:
            return "FITA LED"

    return "Sem categoria"


def _is_description_title(name: str, code: str) -> bool:
    normalized = _normalize_name_for_match(name)
    for marker in ("descricao", "description", "descri"):
        if marker in normalized:
            return True

    code_prefix = str(code).strip()
    if not code_prefix:
        return False
    if not normalized.startswith(code_prefix):
        return False

    remainder = normalized[len(code_prefix) :].lstrip()
    if not remainder.startswith("-"):
        return False
    detail = remainder[1:].strip()
    if not detail:
        return False
    return not re.match(r"^\d+([._-]|$)", detail)


def _local_file_sort_key(file_info: Dict, code: str) -> tuple:
    name = file_info.get("name", "")
    normalized = _normalize_name_for_match(name)
    if _is_description_title(name, code):
        variant = _match_filename(name, str(code))
        if variant is not None and variant > 0:
            base_without_variant = re.sub(
                r"\s*\(\d{1,3}\)(?=\.[^.]+$)",
                "",
                name or "",
                flags=re.IGNORECASE,
            )
            return (0, _normalize_name_for_match(base_without_variant), variant, normalized)
        return (0, normalized)

    variant = _match_filename(name, str(code))
    if variant is not None:
        return (1, variant, normalized)

    return (2, normalized)


def _asset_url(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    return f"/catalog/local/asset?path={quote(normalized, safe='')}"


def _normalize_category_label(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    if cleaned in {"***", "-", "Ã¢â‚¬â€"}:
        return ""
    return cleaned


def _pick_distinct_fallback(files: List[Dict], taken: set[str]) -> Dict | None:
    for item in files:
        rel_path = item.get("rel_path")
        if rel_path and rel_path not in taken:
            return item
    return None


def _code_sort_key(code_value: str) -> tuple[int, int | str]:
    code_text = str(code_value or "").strip()
    if code_text.isdigit():
        return (0, int(code_text))
    return (1, code_text)
