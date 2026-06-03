"""Cadastro persistido de administradores do painel interno."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .core import load_settings
from .representative_registry import hash_representative_password, verify_representative_password


logger = logging.getLogger(__name__)
MANAGED_ADMINS_FILENAME = "admin_users.json"


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _normalize_email(value: Any) -> str:
    return _stringify(value).lower()


def _managed_admins_path() -> Path:
    explicit = _stringify(os.getenv("CATALOG_ADMIN_USERS_FILE"))
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (load_settings().base_dir / "reports" / MANAGED_ADMINS_FILENAME).resolve()


def _normalize_admin_user(item: Any, *, source: str, managed: bool) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    email = _normalize_email(item.get("email") or item.get("login"))
    password = _stringify(item.get("password"))
    password_hash = _stringify(item.get("password_hash") or item.get("passwordHash"))
    name = _stringify(item.get("name")) or email
    if not email or (not password and not password_hash):
        return None

    return {
        "email": email,
        "name": name,
        "password": password,
        "password_hash": password_hash,
        "source": source,
        "managed": managed,
    }


def _load_managed_admins() -> list[dict[str, Any]]:
    target = _managed_admins_path()
    if not target.is_file():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Ignoring invalid admin registry at %s: %s", target, exc)
        return []

    raw_users = payload.get("users") if isinstance(payload, dict) else payload
    if not isinstance(raw_users, list):
        return []

    users: list[dict[str, Any]] = []
    for item in raw_users:
        normalized = _normalize_admin_user(item, source="managed", managed=True)
        if normalized:
            users.append(normalized)
    return users


def _environment_admin() -> list[dict[str, Any]]:
    settings = load_settings()
    password = settings.admin_login_password or settings.erp_admin_token
    if not password:
        return []
    normalized = _normalize_admin_user(
        {
            "email": settings.admin_login_email or "admin",
            "name": settings.admin_login_email or "Administrador",
            "password": password,
        },
        source="environment",
        managed=False,
    )
    return [normalized] if normalized else []


def list_admin_login_users() -> list[dict[str, Any]]:
    users_by_email: dict[str, dict[str, Any]] = {}
    for user in [*_load_managed_admins(), *_environment_admin()]:
        users_by_email.setdefault(user["email"], user)
    return list(users_by_email.values())


def verify_admin_password(user: dict[str, Any], provided_password: str) -> bool:
    return verify_representative_password(user, provided_password)


def hash_admin_password(password: str) -> str:
    return hash_representative_password(password)
