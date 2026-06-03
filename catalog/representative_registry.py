"""Cadastro persistido de representantes para acesso ao catalogo."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .core import load_settings


logger = logging.getLogger(__name__)
MANAGED_USERS_FILENAME = "representative_users.json"
PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390000
PASSWORD_RESET_CODE_BYTES = 9
PASSWORD_RESET_EXPIRES_MINUTES = 60


def _stringify(value: Any) -> str:
    return str(value or "").strip()


def _normalize_email(value: Any) -> str:
    return _stringify(value).lower()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw_value = _stringify(value)
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _managed_users_path() -> Path:
    explicit = _stringify(os.getenv("CATALOG_REPRESENTATIVE_USERS_FILE"))
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (load_settings().base_dir / "reports" / MANAGED_USERS_FILENAME).resolve()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def hash_representative_password(password: str) -> str:
    normalized_password = _stringify(password)
    if not normalized_password:
        raise ValueError("Missing representative password")

    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        normalized_password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_SCHEME}$"
        f"{PASSWORD_HASH_ITERATIONS}$"
        f"{_b64encode(salt)}$"
        f"{_b64encode(derived_key)}"
    )


def verify_representative_password(user: dict[str, Any], provided_password: str) -> bool:
    normalized_password = _stringify(provided_password)
    if not normalized_password:
        return False

    stored_hash = _stringify(user.get("password_hash") or user.get("passwordHash"))
    if stored_hash:
        try:
            scheme, raw_iterations, salt_value, expected_value = stored_hash.split("$", 3)
            if scheme != PASSWORD_HASH_SCHEME:
                return False
            iterations = int(raw_iterations)
            derived_key = hashlib.pbkdf2_hmac(
                "sha256",
                normalized_password.encode("utf-8"),
                _b64decode(salt_value),
                iterations,
            )
        except (ValueError, TypeError):
            logger.warning("Ignoring invalid representative password hash for %s", user.get("email"))
            return False
        return secrets.compare_digest(_b64encode(derived_key), expected_value)

    stored_password = _stringify(user.get("password"))
    if not stored_password:
        return False
    return secrets.compare_digest(stored_password, normalized_password)


def _normalize_login_user(
    item: Any,
    *,
    source: str,
    managed: bool,
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    email = _normalize_email(item.get("email") or item.get("login"))
    password = _stringify(item.get("password"))
    password_hash = _stringify(item.get("password_hash") or item.get("passwordHash"))
    name = _stringify(item.get("name") or item.get("display_name") or email or "Representante")
    if not email or not name:
        return None
    if not password and not password_hash:
        return None

    return {
        "email": email,
        "name": name,
        "password": password,
        "password_hash": password_hash,
        "managed": managed,
        "source": source,
        "created_at": _stringify(item.get("created_at")) or None,
        "updated_at": _stringify(item.get("updated_at")) or None,
    }


def _parse_environment_representatives() -> list[dict[str, Any]]:
    settings = load_settings()
    candidates: list[Any] = []

    raw_users_json = _stringify(settings.representative_users_json)
    if raw_users_json:
        try:
            parsed = json.loads(raw_users_json)
        except json.JSONDecodeError as exc:
            logger.warning("Ignoring invalid representative users JSON: %s", exc)
            parsed = []

        if isinstance(parsed, dict) and isinstance(parsed.get("users"), list):
            candidates.extend(parsed.get("users") or [])
        elif isinstance(parsed, list):
            candidates.extend(parsed)
        elif isinstance(parsed, dict):
            candidates.append(parsed)

    if settings.representative_login_password:
        candidates.append(
            {
                "email": settings.representative_login_email or "",
                "password": settings.representative_login_password,
                "name": settings.representative_login_name
                or settings.representative_login_email
                or "Representante",
            }
        )

    users: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    for item in candidates:
        normalized = _normalize_login_user(item, source="environment", managed=False)
        if not normalized or normalized["email"] in seen_emails:
            continue
        users.append(normalized)
        seen_emails.add(normalized["email"])
    return users


def _load_managed_users_payload() -> dict[str, Any]:
    target = _managed_users_path()
    if not target.is_file():
        return {"users": []}

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Ignoring invalid representative registry at %s: %s", target, exc)
        return {"users": []}

    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {"users": payload}
    return {"users": []}


def _load_managed_users_with_secrets() -> list[dict[str, Any]]:
    payload = _load_managed_users_payload()
    raw_users = payload.get("users") if isinstance(payload, dict) else []
    if not isinstance(raw_users, list):
        raw_users = []

    users: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    for item in raw_users:
        normalized = _normalize_login_user(item, source="managed", managed=True)
        if not normalized or normalized["email"] in seen_emails:
            continue
        users.append(normalized)
        seen_emails.add(normalized["email"])
    return users


def _serialize_managed_user(user: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "email": user["email"],
        "name": user["name"],
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }
    if user.get("password_hash"):
        payload["password_hash"] = user["password_hash"]
    elif user.get("password"):
        payload["password"] = user["password"]
    if user.get("password_reset_token_hash"):
        payload["password_reset_token_hash"] = user["password_reset_token_hash"]
        payload["password_reset_expires_at"] = user.get("password_reset_expires_at")
        payload["password_reset_created_at"] = user.get("password_reset_created_at")
    return payload


def _write_managed_users(users: list[dict[str, Any]]) -> None:
    target = _managed_users_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "users": [_serialize_managed_user(user) for user in users],
        "updated_at": _utcnow_iso(),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_representative_login_users() -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    for source_users in (_load_managed_users_with_secrets(), _parse_environment_representatives()):
        for user in source_users:
            email = user["email"]
            if email in seen_emails:
                continue
            merged.append(user)
            seen_emails.add(email)
    return merged


def _sanitize_admin_user(user: dict[str, Any]) -> dict[str, Any]:
    reset_expires_at = user.get("password_reset_expires_at")
    return {
        "email": user["email"],
        "name": user["name"],
        "managed": bool(user.get("managed")),
        "source": str(user.get("source") or "managed"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "password_reset_expires_at": reset_expires_at,
        "password_reset_pending": bool(reset_expires_at and _is_password_reset_active(user)),
    }


def _hash_password_reset_code(code: str) -> str:
    normalized_code = _stringify(code).upper()
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()


def _is_password_reset_active(user: dict[str, Any]) -> bool:
    if not _stringify(user.get("password_reset_token_hash")):
        return False
    expires_at = _parse_iso_datetime(user.get("password_reset_expires_at"))
    if not expires_at:
        return False
    return expires_at > datetime.now(timezone.utc)


def _generate_password_reset_code() -> str:
    return secrets.token_urlsafe(PASSWORD_RESET_CODE_BYTES).replace("-", "").replace("_", "").upper()[:12]


def _load_managed_users_raw() -> list[dict[str, Any]]:
    payload = _load_managed_users_payload()
    raw_users = payload.get("users") if isinstance(payload, dict) else []
    if not isinstance(raw_users, list):
        return []
    return [item for item in raw_users if isinstance(item, dict)]


def _sanitize_reset_user(user: dict[str, Any]) -> dict[str, Any]:
    return _sanitize_admin_user(
        {
            **user,
            "managed": True,
            "source": "managed",
        }
    )


def build_representative_admin_summary() -> dict[str, Any]:
    merged_users = list_representative_login_users()
    sanitized = sorted(
        (_sanitize_admin_user(user) for user in merged_users),
        key=lambda item: (0 if item["managed"] else 1, item["name"].lower(), item["email"]),
    )
    managed_users = [user for user in sanitized if user["managed"]]
    environment_users = [user for user in sanitized if not user["managed"]]
    return {
        "users": sanitized,
        "total_users": len(sanitized),
        "managed_users": len(managed_users),
        "environment_users": len(environment_users),
    }


def upsert_managed_representative(email: str, name: str, password: str | None = None) -> tuple[bool, dict[str, Any]]:
    normalized_email = _normalize_email(email)
    normalized_name = _stringify(name)
    normalized_password = _stringify(password)
    if not normalized_email:
        raise ValueError("Missing representative email")
    if "@" not in normalized_email:
        raise ValueError("Representative email is invalid")
    if not normalized_name:
        raise ValueError("Missing representative name")

    managed_users = _load_managed_users_with_secrets()
    existing_user = next((user for user in managed_users if user["email"] == normalized_email), None)
    environment_users = {user["email"] for user in _parse_environment_representatives()}
    if normalized_email in environment_users and existing_user is None:
        raise ValueError("Representative email is managed by environment configuration")

    timestamp = _utcnow_iso()
    if existing_user:
        existing_user["name"] = normalized_name
        existing_user["updated_at"] = timestamp
        if normalized_password:
            existing_user["password_hash"] = hash_representative_password(normalized_password)
            existing_user["password"] = ""
        _write_managed_users(managed_users)
        return False, _sanitize_admin_user(existing_user)

    if not normalized_password:
        raise ValueError("Missing representative password")

    created_user = {
        "email": normalized_email,
        "name": normalized_name,
        "password": "",
        "password_hash": hash_representative_password(normalized_password),
        "managed": True,
        "source": "managed",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    managed_users.append(created_user)
    _write_managed_users(managed_users)
    return True, _sanitize_admin_user(created_user)


def delete_managed_representative(email: str) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        raise ValueError("Missing representative email")

    managed_users = _load_managed_users_with_secrets()
    kept_users = [user for user in managed_users if user["email"] != normalized_email]
    if len(kept_users) == len(managed_users):
        raise KeyError(normalized_email)

    _write_managed_users(kept_users)
    return {"deleted": True, "email": normalized_email}


def create_representative_password_reset(email: str) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        raise ValueError("Missing representative email")

    existing_login_user = next((user for user in list_representative_login_users() if user["email"] == normalized_email), None)
    raw_managed_users = _load_managed_users_raw()
    raw_user = next(
        (
            user
            for user in raw_managed_users
            if _normalize_email(user.get("email") or user.get("login")) == normalized_email
        ),
        None,
    )

    if existing_login_user is None and raw_user is None:
        raise KeyError(normalized_email)

    timestamp = _utcnow_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRES_MINUTES)).isoformat()
    reset_code = _generate_password_reset_code()

    if raw_user is None:
        raw_user = {
            "email": normalized_email,
            "name": existing_login_user["name"],
            "created_at": timestamp,
        }
        raw_managed_users.append(raw_user)

    raw_user["email"] = normalized_email
    raw_user["name"] = _stringify(raw_user.get("name")) or (existing_login_user or {}).get("name") or normalized_email
    raw_user["updated_at"] = timestamp
    raw_user["password_reset_token_hash"] = _hash_password_reset_code(reset_code)
    raw_user["password_reset_created_at"] = timestamp
    raw_user["password_reset_expires_at"] = expires_at

    _write_managed_users(raw_managed_users)
    return {
        "reset_code": reset_code,
        "expires_at": expires_at,
        "user": _sanitize_reset_user(raw_user),
    }


def reset_representative_password_with_code(email: str, reset_code: str, new_password: str) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    normalized_code = _stringify(reset_code).upper()
    normalized_password = _stringify(new_password)
    if not normalized_email:
        raise ValueError("Missing representative email")
    if not normalized_code:
        raise ValueError("Missing reset code")
    if not normalized_password:
        raise ValueError("Missing new password")
    if len(normalized_password) < 6:
        raise ValueError("New password must have at least 6 characters")

    raw_managed_users = _load_managed_users_raw()
    raw_user = next(
        (
            user
            for user in raw_managed_users
            if _normalize_email(user.get("email") or user.get("login")) == normalized_email
        ),
        None,
    )
    if raw_user is None:
        raise KeyError(normalized_email)

    if not _is_password_reset_active(raw_user):
        raise ValueError("Reset code expired or unavailable")

    expected_hash = _stringify(raw_user.get("password_reset_token_hash"))
    if not secrets.compare_digest(expected_hash, _hash_password_reset_code(normalized_code)):
        raise ValueError("Invalid reset code")

    timestamp = _utcnow_iso()
    raw_user["email"] = normalized_email
    raw_user["name"] = _stringify(raw_user.get("name")) or normalized_email
    raw_user["password"] = ""
    raw_user["password_hash"] = hash_representative_password(normalized_password)
    raw_user["updated_at"] = timestamp
    raw_user.pop("password_reset_token_hash", None)
    raw_user.pop("password_reset_created_at", None)
    raw_user.pop("password_reset_expires_at", None)

    _write_managed_users(raw_managed_users)
    return _sanitize_reset_user(raw_user)
