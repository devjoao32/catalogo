"""Montagem do catalogo local com cadastro, ERP e fallback de estoque."""

from __future__ import annotations

import logging
import os
import re
from typing import Callable, Dict, List

from .technical_specs import resolve_technical_specs


logger = logging.getLogger(__name__)


def _normalize_category_label(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    if cleaned in {"***", "-", "Ã¢â‚¬â€", "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â"}:
        return ""
    return cleaned


def load_cadastro_records(path_override: str | None = None) -> Dict[str, Dict[str, str]]:
    cadastro_path = os.getenv("CATALOG_CADASTRO_HTML")
    if path_override is not None and not cadastro_path:
        return {}

    try:
        from .cadastro import load_cadastro_index

        return load_cadastro_index(cadastro_path)
    except Exception as exc:
        logger.warning("Failed to load cadastro index: %s", exc, exc_info=True)
        return {}


def _stringify(value: object) -> str:
    return str(value or "").strip()


def _is_placeholder_photo(value: object) -> bool:
    text = _stringify(value).lower()
    return not text or "placehold.co" in text


def _first_real_photo(*values: object) -> str:
    for value in values:
        text = _stringify(value)
        if text and not _is_placeholder_photo(text):
            return text
    return ""


def _needs_resolved_photos(product: Dict) -> bool:
    return any(
        _is_placeholder_photo(product.get(field))
        for field in ("URLFoto", "FotoBranco", "FotoAmbient", "FotoMedidas")
    )


def _resolved_photo_fields(record: Dict, asset_url: Callable[[str], str]) -> Dict[str, str]:
    variants = record.get("variants", {})
    white = variants.get("white_background")
    ambient = variants.get("ambient")
    measures = variants.get("measures")

    white_url = asset_url(white["rel_path"]) if white else ""
    ambient_url = asset_url(ambient["rel_path"]) if ambient else ""
    measures_url = asset_url(measures["rel_path"]) if measures else ""
    cover_url = _first_real_photo(ambient_url, white_url, measures_url)
    return {
        "URLFoto": cover_url,
        "FotoBranco": white_url or cover_url,
        "FotoAmbient": ambient_url,
        "FotoMedidas": measures_url,
    }


def _apply_resolved_photos(product: Dict, resolved_fields: Dict[str, str]) -> Dict:
    merged = dict(product)

    existing_cover = _stringify(merged.get("URLFoto"))
    resolved_cover = _stringify(resolved_fields.get("URLFoto"))

    existing_white = _stringify(merged.get("FotoBranco")) or existing_cover
    resolved_white = _stringify(resolved_fields.get("FotoBranco")) or resolved_cover
    white = _first_real_photo(resolved_white, existing_white, existing_cover)

    existing_ambient = _stringify(merged.get("FotoAmbient"))
    resolved_ambient = _stringify(resolved_fields.get("FotoAmbient"))
    ambient = _first_real_photo(resolved_ambient, existing_ambient)

    existing_measures = _stringify(merged.get("FotoMedidas"))
    resolved_measures = _stringify(resolved_fields.get("FotoMedidas"))
    measures = _first_real_photo(resolved_measures, existing_measures)

    cover = _first_real_photo(ambient, white, measures, resolved_cover, existing_cover)

    if cover:
        merged["URLFoto"] = cover
    if white:
        merged["FotoBranco"] = white
    elif cover:
        merged["FotoBranco"] = cover
    if ambient:
        merged["FotoAmbient"] = ambient
    if measures:
        merged["FotoMedidas"] = measures

    return merged


def _enrich_products_with_resolved_photos(
    products: List[Dict],
    *,
    local_index: Dict[str, Dict],
    get_stock_photo_records_for_codes: Callable[[set[str]], Dict[str, Dict]],
    asset_url: Callable[[str], str],
) -> List[Dict]:
    pending_stock_codes = {
        _stringify(item.get("Codigo"))
        for item in products
        if _needs_resolved_photos(item) and _stringify(item.get("Codigo")) not in local_index
    }
    stock_records = get_stock_photo_records_for_codes(pending_stock_codes) if pending_stock_codes else {}

    enriched: List[Dict] = []
    for item in products:
        code = _stringify(item.get("Codigo"))
        record = local_index.get(code) or stock_records.get(code)
        if not record:
            enriched.append(_apply_resolved_photos(item, {}))
            continue
        enriched.append(_apply_resolved_photos(item, _resolved_photo_fields(record, asset_url)))
    return enriched


def _resolve_product_record(
    code: str,
    path_override: str | None,
    get_local_index: Callable[[str | None], Dict[str, Dict]],
    get_stock_photo_record_for_code: Callable[[str], Dict | None],
) -> Dict | None:
    record = get_local_index(path_override).get(str(code))
    if record:
        return record
    return get_stock_photo_record_for_code(str(code))


def list_local_products(
    path_override: str | None,
    *,
    get_local_index: Callable[[str | None], Dict[str, Dict]],
    load_stock_products: Callable[[], List[Dict]],
    enrich_stock_products_with_photos: Callable[[List[Dict]], List[Dict]],
    get_stock_photo_records_for_codes: Callable[[set[str]], Dict[str, Dict]],
    asset_url: Callable[[str], str],
    canonical_category: Callable[[str, str], str],
    code_sort_key: Callable[[str], tuple[int, int | str]],
) -> List[Dict]:
    from .erp_catalog import merge_products_with_erp
    from .nitrolux_db import merge_products_with_nitrolux
    from .stock_catalog import merge_products_with_stock_sales

    index = get_local_index(path_override)
    if not index and path_override is None:
        stock_products = load_stock_products()
        if stock_products:
            enriched_stock_products = enrich_stock_products_with_photos(stock_products)
            merged_stock_products = merge_products_with_erp(enriched_stock_products)
            merged_stock_products = merge_products_with_stock_sales(merged_stock_products)
            return merge_products_with_nitrolux(merged_stock_products)

    cadastro_records = load_cadastro_records(path_override)
    products: List[Dict] = []
    for code, record in sorted(index.items(), key=lambda item: code_sort_key(item[0])):
        variants = record.get("variants", {})
        white = variants.get("white_background")
        ambient = variants.get("ambient")
        measures = variants.get("measures")

        white_url = asset_url(white["rel_path"]) if white else ""
        ambient_url = asset_url(ambient["rel_path"]) if ambient else ""
        measures_url = asset_url(measures["rel_path"]) if measures else ""
        cover_url = _first_real_photo(ambient_url, white_url, measures_url)

        cadastro = cadastro_records.get(str(code), {})
        merged_name = str(cadastro.get("name") or record.get("name") or f"Produto {code}").strip()
        merged_description = str(cadastro.get("description") or "").strip()
        merged_specs = resolve_technical_specs(
            code=code,
            current_specs=cadastro.get("specs"),
            name=merged_name,
            description=merged_description,
            category=cadastro.get("category") or record.get("category") or "",
            extra_fields={**record, **cadastro},
        )
        cadastro_category = _normalize_category_label(str(cadastro.get("category") or ""))
        if cadastro_category:
            merged_category = cadastro_category
        else:
            merged_category_source = _normalize_category_label(
                str(record.get("category") or "Sem categoria")
            )
            merged_category = canonical_category(merged_category_source, merged_name)

        products.append(
            {
                "Codigo": code,
                "Nome": merged_name,
                "Descricao": merged_description,
                "Categoria": merged_category,
                "URLFoto": cover_url,
                "Especificacoes": merged_specs,
                "FotoBranco": white_url or cover_url,
                "FotoAmbient": ambient_url,
                "FotoMedidas": measures_url,
            }
        )

    merged_products = merge_products_with_erp(products)
    merged_products = merge_products_with_stock_sales(merged_products)
    if path_override is not None:
        return merge_products_with_nitrolux(merged_products)

    resolved_products = _enrich_products_with_resolved_photos(
        merged_products,
        local_index=index,
        get_stock_photo_records_for_codes=get_stock_photo_records_for_codes,
        asset_url=asset_url,
    )
    return merge_products_with_nitrolux(resolved_products)


def categorize_local_photos(
    code: str,
    path_override: str | None,
    *,
    get_local_index: Callable[[str | None], Dict[str, Dict]],
    get_stock_photo_record_for_code: Callable[[str], Dict | None],
    asset_url: Callable[[str], str],
) -> Dict[str, str | None]:
    record = _resolve_product_record(
        str(code),
        path_override,
        get_local_index,
        get_stock_photo_record_for_code,
    )
    if not record:
        return {"white_background": None, "ambient": None, "measures": None}

    variants = record.get("variants", {})
    return {
        "white_background": asset_url(variants["white_background"]["rel_path"])
        if variants.get("white_background")
        else None,
        "ambient": asset_url(variants["ambient"]["rel_path"]) if variants.get("ambient") else None,
        "measures": asset_url(variants["measures"]["rel_path"]) if variants.get("measures") else None,
    }


def find_local_images_for_code(
    code: str,
    path_override: str | None,
    *,
    get_local_index: Callable[[str | None], Dict[str, Dict]],
    get_stock_photo_record_for_code: Callable[[str], Dict | None],
    local_file_sort_key: Callable[[Dict, str], tuple],
    asset_url: Callable[[str], str],
) -> List[Dict]:
    record = _resolve_product_record(
        str(code),
        path_override,
        get_local_index,
        get_stock_photo_record_for_code,
    )
    if not record:
        return []

    ordered_files = sorted(
        record.get("files", []),
        key=lambda item: local_file_sort_key(item, str(code)),
    )
    images: List[Dict] = []
    for idx, file_info in enumerate(ordered_files):
        images.append(
            {
                "name": file_info.get("name", ""),
                "variant": idx,
                "url": asset_url(file_info.get("rel_path", "")),
            }
        )
    return images


def resolve_local_asset_path(
    rel_path: str,
    path_override: str | None,
    *,
    existing_local_roots: Callable[[str | None], List[str]],
    resolve_stock_photos_root: Callable[[str | None], str | None],
) -> str | None:
    roots = existing_local_roots(path_override)
    stock_root = resolve_stock_photos_root(path_override)
    if stock_root and stock_root.lower() not in {root.lower() for root in roots}:
        roots = [stock_root, *roots]
    if not roots or not rel_path:
        return None

    normalized = rel_path.replace("/", os.sep).replace("\\", os.sep)
    for root in roots:
        candidate = os.path.abspath(os.path.join(root, normalized))
        try:
            within_root = os.path.commonpath([root, candidate]) == root
        except ValueError:
            continue
        if within_root and os.path.isfile(candidate):
            return candidate
    return None
