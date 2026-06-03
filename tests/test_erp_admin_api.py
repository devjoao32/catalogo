import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app import app


def _reports_test_path(filename: str) -> Path:
    return Path(os.getcwd()) / "reports" / filename


def test_erp_products_endpoint_lists_active_payload(monkeypatch):
    target_path = _reports_test_path("_test_erp_admin_list.json")
    if target_path.exists():
        target_path.unlink()

    try:
        target_path.write_text(
            json.dumps(
                {
                    "imported_at": "2026-04-09T10:00:00+00:00",
                    "products": [
                        {
                            "Codigo": "9911",
                            "Nome": "Produto ERP",
                            "Categoria": "LUMINARIA",
                            "Descricao": "Descricao ativa",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("CATALOG_ERP_JSON_PATH", str(target_path))

        client = TestClient(app)
        response = client.get("/catalog/erp/products")

        assert response.status_code == 200
        payload = response.json()
        assert payload["exists"] is True
        assert payload["products_loaded"] == 1
        assert payload["path"] == str(target_path)
        assert payload["products"][0]["Codigo"] == "9911"
    finally:
        if target_path.exists():
            target_path.unlink()


def test_erp_products_upsert_updates_existing_product(monkeypatch):
    target_path = _reports_test_path("_test_erp_admin_update.json")
    if target_path.exists():
        target_path.unlink()

    try:
        target_path.write_text(
            json.dumps(
                {
                    "imported_at": "2026-04-09T10:00:00+00:00",
                    "source": "seed",
                    "products": [
                        {
                            "Codigo": "9911",
                            "Nome": "Produto Antigo",
                            "Categoria": "LUMINARIA",
                            "Descricao": "Descricao antiga",
                            "voltagem": "110V",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("CATALOG_ERP_JSON_PATH", str(target_path))

        client = TestClient(app)
        response = client.put(
            "/catalog/erp/products/9911",
            json={
                "Nome": "Produto Atualizado",
                "Categoria": "PENDENTE",
                "Descricao": "Descricao nova",
                "voltagem": "220V",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] is False
        assert payload["code"] == "9911"
        assert payload["product"]["Nome"] == "Produto Atualizado"
        assert payload["product"]["voltagem"] == "220V"

        stored = json.loads(target_path.read_text(encoding="utf-8"))
        assert stored["source"] == "seed"
        assert stored["products"][0]["Codigo"] == "9911"
        assert stored["products"][0]["Nome"] == "Produto Atualizado"
        assert stored["products"][0]["voltagem"] == "220V"
    finally:
        if target_path.exists():
            target_path.unlink()


def test_erp_products_upsert_creates_new_file_and_product(monkeypatch):
    target_path = _reports_test_path("_test_erp_admin_create.json")
    if target_path.exists():
        target_path.unlink()

    try:
        monkeypatch.setenv("CATALOG_ERP_JSON_PATH", str(target_path))

        client = TestClient(app)
        response = client.put(
            "/catalog/erp/products/8877",
            json={
                "Nome": "Produto Novo",
                "Categoria": "ARANDELA",
                "Descricao": "Criado pela area administrativa",
                "Especificacoes": "Potencia: 12W",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] is True
        assert payload["products_loaded"] == 1
        assert payload["product"]["Codigo"] == "8877"
        assert payload["product"]["Nome"] == "Produto Novo"
        assert target_path.exists()

        stored = json.loads(target_path.read_text(encoding="utf-8"))
        assert stored["products"][0]["Codigo"] == "8877"
        assert stored["products"][0]["Nome"] == "Produto Novo"
    finally:
        if target_path.exists():
            target_path.unlink()
