"""Enriquecimento opcional de produtos com dados do PostgreSQL Nitrolux."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Sequence


logger = logging.getLogger(__name__)
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_code(value: Any) -> str:
    text = _stringify(value)
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return text.split(".")[0]
    return text


def _quote_identifier(value: str) -> str:
    identifier = _stringify(value)
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"invalid PostgreSQL identifier: {identifier!r}")
    return f'"{identifier}"'


@dataclass(frozen=True)
class NitroluxDbConfig:
    enabled: bool
    url: str | None
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str
    schema: str
    table: str
    code_column: str
    package_column: str
    master_box_column: str

    @property
    def is_configured(self) -> bool:
        if not self.enabled:
            return False
        if self.url:
            return True
        return bool(self.user)


def load_nitrolux_db_config() -> NitroluxDbConfig:
    configured_port = _stringify(os.getenv("CATALOG_NITROLUX_DB_PORT")) or "5432"
    try:
        port = int(configured_port)
    except ValueError as exc:
        raise ValueError("CATALOG_NITROLUX_DB_PORT must be an integer") from exc

    return NitroluxDbConfig(
        enabled=_env_flag("CATALOG_NITROLUX_DB_ENABLED", default=False),
        url=_stringify(os.getenv("CATALOG_NITROLUX_DB_URL")) or None,
        host=_stringify(os.getenv("CATALOG_NITROLUX_DB_HOST")) or "127.0.0.1",
        port=port,
        database=_stringify(os.getenv("CATALOG_NITROLUX_DB_NAME")) or "nitrolux",
        user=_stringify(os.getenv("CATALOG_NITROLUX_DB_USER")),
        password=_stringify(os.getenv("CATALOG_NITROLUX_DB_PASSWORD")),
        sslmode=_stringify(os.getenv("CATALOG_NITROLUX_DB_SSLMODE")) or "prefer",
        schema=_stringify(os.getenv("CATALOG_NITROLUX_DB_SCHEMA")) or "public",
        table=_stringify(os.getenv("CATALOG_NITROLUX_DB_TABLE")) or "pcprodut",
        code_column=_stringify(os.getenv("CATALOG_NITROLUX_DB_CODE_COLUMN")) or "codprod",
        package_column=_stringify(os.getenv("CATALOG_NITROLUX_DB_PACKAGE_COLUMN")) or "embalagem",
        master_box_column=_stringify(os.getenv("CATALOG_NITROLUX_DB_MASTER_BOX_COLUMN")) or "caixa_master",
    )


def _connect(config: NitroluxDbConfig):
    try:
        import psycopg
    except ImportError:
        logger.warning(
            "Nitrolux PostgreSQL enrichment is enabled but psycopg is not installed. "
            "Install dependencies from requirements.txt."
        )
        return None

    connect_kwargs = {"connect_timeout": 5}
    if config.url:
        return psycopg.connect(config.url, **connect_kwargs)

    return psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
        sslmode=config.sslmode,
        **connect_kwargs,
    )


def _fetch_packaging_rows(config: NitroluxDbConfig, codes: Sequence[str]) -> List[tuple[Any, Any, Any]]:
    if not codes:
        return []

    qualified_table = ".".join(
        [
            _quote_identifier(config.schema),
            _quote_identifier(config.table),
        ]
    )
    code_column = _quote_identifier(config.code_column)
    package_column = _quote_identifier(config.package_column)
    master_box_column = _quote_identifier(config.master_box_column)
    query = (
        f"SELECT {code_column}::text AS codigo, "
        f"{package_column}::text AS embalagem, "
        f"{master_box_column}::text AS caixa_master "
        f"FROM {qualified_table} "
        f"WHERE {code_column}::text = ANY(%s)"
    )

    connection = _connect(config)
    if connection is None:
        return []

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (list(codes),))
            rows = cursor.fetchall()
    return rows


def load_packaging_index(codes: Iterable[Any]) -> Dict[str, Dict[str, str]]:
    normalized_codes = [
        normalized
        for normalized in dict.fromkeys(_normalize_code(item) for item in codes)
        if normalized
    ]
    if not normalized_codes:
        return {}

    config = load_nitrolux_db_config()
    if not config.is_configured:
        return {}

    try:
        rows = _fetch_packaging_rows(config, normalized_codes)
    except Exception as exc:
        logger.warning("Nitrolux PostgreSQL enrichment failed: %s", exc)
        return {}

    index: Dict[str, Dict[str, str]] = {}
    for row in rows:
        code, package, master_box = row
        normalized_code = _normalize_code(code)
        if not normalized_code:
            continue
        entry: Dict[str, str] = {}
        package_value = _stringify(package)
        master_box_value = _stringify(master_box)
        if package_value:
            entry["Embalagem"] = package_value
        if master_box_value:
            entry["CaixaMaster"] = master_box_value
        if entry:
            index[normalized_code] = entry
    return index


def merge_products_with_nitrolux(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not products:
        return products

    packaging_index = load_packaging_index(product.get("Codigo") for product in products)
    if not packaging_index:
        return products

    merged_products: List[Dict[str, Any]] = []
    for product in products:
        code = _normalize_code(product.get("Codigo"))
        extra = packaging_index.get(code)
        if not extra:
            merged_products.append(product)
            continue

        merged = dict(product)
        for field, value in extra.items():
            if value:
                merged[field] = value
        merged_products.append(merged)

    return merged_products
