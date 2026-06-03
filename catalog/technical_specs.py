"""Technical specs lookup and lightweight inference helpers."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TECHNICAL_SPECS_PATH = BASE_DIR / "reports" / "technical_specs.txt"
ENTRY_START_PATTERN = re.compile(r'(?im)^[\s"\'`*]*c[oó]digo\s*:')
CODE_PATTERN = re.compile(r"c[oó]digo\s*:\s*([A-Za-z0-9._/-]+)", re.IGNORECASE)
REFERENCE_PATTERN = re.compile(r"\b([A-Z]{1,}[A-Z0-9./-]*\d+[A-Z0-9./-]*)\b")
POWER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?(?:\s*x\s*\d+(?:[.,]\d+)?)?\s*W(?:/M)?\b", re.IGNORECASE)
BASE_PATTERN = re.compile(
    r"\b(E27/E40|E27/40|E27|E14|E40|GU10|G9X\d+|G9|G13|SMD|COB)\b",
    re.IGNORECASE,
)
FLUX_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\s*LM(?:/\w+)?\b", re.IGNORECASE)
COLOR_TEMP_PATTERN = re.compile(
    r"\b(?:\d{4,5}\s*K(?:\s*[+/]\s*\d{4,5}\s*K)*)\b|\b3\s*EM\s*1\b",
    re.IGNORECASE,
)
VOLTAGE_PATTERN = re.compile(
    r"\b(?:AC|DC)?\s*\d+(?:[.,]\d+)?(?:\s*[-/]\s*\d+(?:[.,]\d+)?)?\s*V\b|\bBIVOLT\b",
    re.IGNORECASE,
)
LENGTH_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\s*M\b(?!M)", re.IGNORECASE)
DIMENSIONS_PATTERN = re.compile(
    r"(?:Ø\s*)?\d+(?:[.,]\d+)?(?:\s*[xX]\s*(?:Ø\s*)?\d+(?:[.,]\d+)?){1,3}\s*MM\b",
    re.IGNORECASE,
)
IP_PATTERN = re.compile(r"\bIP\s*\d{2}\b", re.IGNORECASE)
CRI_PATTERN = re.compile(r"\b(?:IRC|CRI)\s*[=:]?\s*[><=]*\s*\d{2,3}\b", re.IGNORECASE)
POWER_FACTOR_PATTERN = re.compile(r"\b(?:FP|FATOR\s+DE\s+POTENCIA)\s*[=:]?\s*[><=]*\s*\d+(?:[.,]\d+)?\b", re.IGNORECASE)
MATERIAL_PATTERN = re.compile(
    r"\b(ALUMINIO|ALUMINI|ALUMI|ALUM|METAL|VIDRO|CRISTAL|MADEIRA|BAMBU|LINHO|PVC|ABS|PC|PS|ACRILICO|SILICONE|PAPEL|ACO|INOX)\b",
    re.IGNORECASE,
)
WARRANTY_PATTERN = re.compile(r"\b\d+\s*(?:ANO|ANOS|MES|MESES)\b", re.IGNORECASE)

FIELD_ALIASES = {
    "REFERENCIA": ("referencia", "ref", "modelo"),
    "POTENCIA(W)": ("potencia", "potenciaw", "potencianominal", "potenciamaxima", "potenciamax"),
    "BASE": ("base",),
    "FLUXO LUMINOSO": ("fluxoluminoso", "lumens", "luminousflux"),
    "TEMP. COR(K)": ("tempcor", "temperaturadecor", "tempdecor", "tempcork"),
    "TENSAO(V)": ("tensao", "voltagem", "tensaonominal"),
    "COMPRIMENTO": ("comprimento",),
    "DIMENSOES": ("dimensao", "dimensoes", "medidas"),
    "IRC": ("irc", "cri"),
    "FATOR DE POTENCIA": ("fatorpotencia", "fp"),
    "MATERIAL": ("material", "materialpredominante"),
    "INDICE DE PROTECAO": ("indicedeprotecao", "ip", "protecao"),
    "GARANTIA": ("garantia",),
}

REFERENCE_STOPWORDS = {
    "ABS",
    "AC",
    "ALUM",
    "ALUMI",
    "ALUMINIO",
    "BASE",
    "BIVOLT",
    "BRANCA",
    "BRANCO",
    "CODIGO",
    "COR",
    "CRISTAL",
    "DOURADO",
    "E14",
    "E27",
    "E40",
    "GARANTIA",
    "G13",
    "G9",
    "GU10",
    "IP20",
    "IP65",
    "IP66",
    "IP67",
    "LED",
    "LINHO",
    "LUZ",
    "MADEIRA",
    "METAL",
    "PC",
    "PERFIL",
    "PRETO",
    "PS",
    "PVC",
    "RGB",
    "SMD",
    "SOBREPOR",
    "TENSAO",
    "VIDRO",
}


def _resolve_technical_specs_path() -> Path:
    explicit = os.getenv("CATALOG_TECHNICAL_SPECS_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return DEFAULT_TECHNICAL_SPECS_PATH


def _normalize_code(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _stringify(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _split_entries(raw_text: str) -> list[str]:
    text = str(raw_text or "").replace("\ufeff", "")
    matches = list(ENTRY_START_PATTERN.finditer(text))
    if not matches:
        return []

    entries: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entry = text[start:end].strip()
        if entry:
            entries.append(entry)
    return entries


def _normalize_entry_text(raw_entry: str) -> str:
    text = str(raw_entry or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s*\\+\s*", "\n", text)
    lines = []
    for line in text.split("\n"):
        cleaned = re.sub(r"\s+", " ", line).strip(' "\'`*')
        if not cleaned or cleaned == "***":
            continue
        lines.append(cleaned)
    return " | ".join(lines).strip(" |")


def _normalize_freeform_specs(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "\\" in text or "\n" in text or "\r" in text:
        return _normalize_entry_text(text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def load_technical_specs_map() -> Dict[str, str]:
    path = _resolve_technical_specs_path()
    if not path.is_file():
        return {}

    raw_text = path.read_text(encoding="utf-8")
    specs_map: Dict[str, str] = {}
    for entry in _split_entries(raw_text):
        match = CODE_PATTERN.search(entry)
        if not match:
            continue
        code = _normalize_code(match.group(1))
        if not re.fullmatch(r"\d{3,12}", code):
            continue
        normalized_entry = _normalize_entry_text(entry)
        if not normalized_entry:
            continue
        previous = specs_map.get(code, "")
        if len(normalized_entry) >= len(previous):
            specs_map[code] = normalized_entry
    return specs_map


def clear_technical_specs_cache() -> None:
    load_technical_specs_map.cache_clear()


def get_technical_specs_for_code(code: object) -> str:
    normalized_code = _normalize_code(code)
    if not normalized_code:
        return ""
    return load_technical_specs_map().get(normalized_code, "")


def _build_lookup(extra_fields: Mapping[str, object] | None) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    if not extra_fields:
        return lookup

    for key, value in extra_fields.items():
        rendered = _stringify(value)
        if not rendered:
            continue
        lookup[_normalize_key(key)] = rendered
    return lookup


def _pick_lookup_value(lookup: Mapping[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = lookup.get(_normalize_key(alias), "")
        if value:
            return value
    return ""


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" |").upper()


def _first_pattern_match(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return _clean_value(match.group(0))


def _extract_reference(text: str, code: str) -> str:
    for match in REFERENCE_PATTERN.finditer(text):
        candidate = _clean_value(match.group(1))
        candidate_code = _normalize_code(candidate)
        compact = candidate.replace(" ", "")
        if candidate in REFERENCE_STOPWORDS:
            continue
        if candidate_code and candidate_code == code:
            continue
        if compact.endswith("MM") and "X" in compact:
            continue
        if compact.endswith("K") or compact.endswith("V") or compact.endswith("W"):
            continue
        if compact.startswith("IP") and compact[2:].isdigit():
            continue
        if compact.endswith("M") and compact[:-1].replace(".", "").isdigit():
            continue
        return candidate
    return ""


def _normalize_material_token(token: str) -> str:
    upper = _clean_value(token)
    if upper.startswith("ALUM"):
        return "ALUMINIO"
    if upper.startswith("ACRIL"):
        return "ACRILICO"
    if upper.startswith("ACO") or upper == "INOX":
        return "ACO"
    return upper


def _extract_material(text: str, lookup: Mapping[str, str]) -> str:
    explicit = _pick_lookup_value(lookup, FIELD_ALIASES["MATERIAL"])
    if explicit:
        return _clean_value(explicit)

    found: list[str] = []
    for match in MATERIAL_PATTERN.finditer(text):
        token = _normalize_material_token(match.group(1))
        if token not in found:
            found.append(token)
    return " + ".join(found[:3])


def _build_search_text(
    *,
    code: object,
    name: object,
    description: object,
    category: object,
    extra_fields: Mapping[str, object] | None,
) -> str:
    parts = [
        _stringify(code),
        _stringify(name),
        _stringify(description),
        _stringify(category),
    ]
    if extra_fields:
        parts.extend(_stringify(value) for value in extra_fields.values())
    return " | ".join(part for part in parts if part).upper()


def _infer_technical_specs(
    *,
    code: object,
    name: object = "",
    description: object = "",
    category: object = "",
    extra_fields: Mapping[str, object] | None = None,
) -> str:
    lookup = _build_lookup(extra_fields)
    search_text = _build_search_text(
        code=code,
        name=name,
        description=description,
        category=category,
        extra_fields=extra_fields,
    )

    normalized_code = _normalize_code(code)
    output_code = normalized_code or _clean_value(_stringify(code))

    fields: list[tuple[str, str]] = []
    if output_code:
        fields.append(("CODIGO", output_code))

    reference = _pick_lookup_value(lookup, FIELD_ALIASES["REFERENCIA"]) or _extract_reference(search_text, normalized_code)
    power = _pick_lookup_value(lookup, FIELD_ALIASES["POTENCIA(W)"]) or _first_pattern_match(search_text, POWER_PATTERN)
    base = _pick_lookup_value(lookup, FIELD_ALIASES["BASE"]) or _first_pattern_match(search_text, BASE_PATTERN)
    flux = _pick_lookup_value(lookup, FIELD_ALIASES["FLUXO LUMINOSO"]) or _first_pattern_match(search_text, FLUX_PATTERN)
    color_temp = _pick_lookup_value(lookup, FIELD_ALIASES["TEMP. COR(K)"]) or _first_pattern_match(search_text, COLOR_TEMP_PATTERN)
    voltage = _pick_lookup_value(lookup, FIELD_ALIASES["TENSAO(V)"]) or _first_pattern_match(search_text, VOLTAGE_PATTERN)
    length = _pick_lookup_value(lookup, FIELD_ALIASES["COMPRIMENTO"]) or _first_pattern_match(search_text, LENGTH_PATTERN)
    dimensions = _pick_lookup_value(lookup, FIELD_ALIASES["DIMENSOES"]) or _first_pattern_match(search_text, DIMENSIONS_PATTERN)
    cri = _pick_lookup_value(lookup, FIELD_ALIASES["IRC"]) or _first_pattern_match(search_text, CRI_PATTERN)
    power_factor = _pick_lookup_value(lookup, FIELD_ALIASES["FATOR DE POTENCIA"]) or _first_pattern_match(search_text, POWER_FACTOR_PATTERN)
    material = _extract_material(search_text, lookup)
    protection = _pick_lookup_value(lookup, FIELD_ALIASES["INDICE DE PROTECAO"]) or _first_pattern_match(search_text, IP_PATTERN)
    warranty = _pick_lookup_value(lookup, FIELD_ALIASES["GARANTIA"]) or _first_pattern_match(search_text, WARRANTY_PATTERN)

    inferred_fields = [
        ("REFERENCIA", reference),
        ("POTENCIA(W)", power),
        ("BASE", base),
        ("FLUXO LUMINOSO", flux),
        ("TEMP. COR(K)", color_temp),
        ("TENSAO(V)", voltage),
        ("COMPRIMENTO", length),
        ("DIMENSOES", dimensions),
        ("IRC", cri),
        ("FATOR DE POTENCIA", power_factor),
        ("MATERIAL", material),
        ("INDICE DE PROTECAO", protection),
        ("GARANTIA", warranty),
    ]

    for label, value in inferred_fields:
        cleaned = _clean_value(value)
        if cleaned:
            fields.append((label, cleaned))

    if len(fields) <= 1:
        return ""

    return " | ".join(f"{label}: {value}" for label, value in fields)


def resolve_technical_specs(
    *,
    code: object,
    current_specs: object = "",
    name: object = "",
    description: object = "",
    category: object = "",
    extra_fields: Mapping[str, object] | None = None,
) -> str:
    explicit_specs = _normalize_freeform_specs(current_specs)
    if explicit_specs:
        return explicit_specs

    by_code = get_technical_specs_for_code(code)
    if by_code:
        return by_code

    return _infer_technical_specs(
        code=code,
        name=name,
        description=description,
        category=category,
        extra_fields=extra_fields,
    )
