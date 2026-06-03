"""Redefine a senha local do administrador/representante.

Uso:
    python scripts/reset_access_password.py --email suporte.recife@nitrolux.com.br --password "nova-senha"
    python scripts/reset_access_password.py --email suporte.recife@nitrolux.com.br --generate
"""

from __future__ import annotations

import argparse
import secrets
import string
from pathlib import Path


ENV_KEYS = {
    "CATALOG_ADMIN_LOGIN_EMAIL",
    "CATALOG_ADMIN_LOGIN_PASSWORD",
    "CATALOG_REPRESENTATIVE_LOGIN_EMAIL",
    "CATALOG_REPRESENTATIVE_LOGIN_PASSWORD",
    "CATALOG_REPRESENTATIVE_LOGIN_NAME",
}


def _build_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%*?"
    return "".join(secrets.choice(alphabet) for _ in range(16))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Redefine o acesso local usado pelo painel interno e pelo login de representante."
    )
    parser.add_argument("--email", required=True, help="E-mail do administrador/representante.")
    parser.add_argument("--name", default="", help="Nome exibido para o representante.")
    password_group = parser.add_mutually_exclusive_group(required=True)
    password_group.add_argument("--password", help="Nova senha.")
    password_group.add_argument("--generate", action="store_true", help="Gera uma senha temporaria forte.")
    return parser.parse_args()


def _validate_secret(value: str, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise SystemExit(f"{label} nao pode ficar vazio.")
    if "\n" in normalized or "\r" in normalized:
        raise SystemExit(f"{label} nao pode conter quebra de linha.")
    return normalized


def _upsert_env_value(lines: list[str], key: str, value: str) -> list[str]:
    replacement = f"{key}={value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[index] = replacement
            return lines
    lines.append(replacement)
    return lines


def _update_env_file(env_path: Path, email: str, password: str, name: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    values = {
        "CATALOG_ADMIN_LOGIN_EMAIL": email,
        "CATALOG_ADMIN_LOGIN_PASSWORD": password,
        "CATALOG_REPRESENTATIVE_LOGIN_EMAIL": email,
        "CATALOG_REPRESENTATIVE_LOGIN_PASSWORD": password,
        "CATALOG_REPRESENTATIVE_LOGIN_NAME": name or email,
    }
    for key in ENV_KEYS:
        lines = _upsert_env_value(lines, key, values[key])
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    email = _validate_secret(args.email.lower(), "E-mail")
    password = _build_password() if args.generate else _validate_secret(args.password, "Senha")
    name = str(args.name or "").strip() or email

    project_root = Path(__file__).resolve().parents[1]
    _update_env_file(project_root / ".env", email, password, name)

    print("Senha redefinida com sucesso.")
    print(f"E-mail: {email}")
    print(f"Senha: {password}")
    print("Reinicie o backend para aplicar a alteracao.")


if __name__ == "__main__":
    main()
