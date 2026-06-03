from fastapi.testclient import TestClient

from app import app


def test_google_drive_images_route_matches_product_code(monkeypatch):
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_FOLDER_ID", "drive-folder")
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "catalog.google_drive.list_google_drive_images",
        lambda folder_id=None: [
            {
                "id": "file-1",
                "name": "1234 (1).jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=file-1",
            },
            {
                "id": "file-2",
                "name": "1234 (2).jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=file-2",
            },
            {
                "id": "file-3",
                "name": "9999.jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=file-3",
            },
        ],
    )

    client = TestClient(app)
    response = client.get("/catalog/google-drive/produtos/1234/imagens")

    assert response.status_code == 200
    payload = response.json()
    assert payload["codigo"] == "1234"
    assert [item["name"] for item in payload["imagens"]] == ["1234 (1).jpg", "1234 (2).jpg"]
    assert payload["imagens"][0]["variant"] == 1


def test_google_drive_photos_route_categorizes_variants(monkeypatch):
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_FOLDER_ID", "drive-folder")
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "catalog.google_drive.list_google_drive_images",
        lambda folder_id=None: [
            {
                "id": "white",
                "name": "1234 (1).jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=white",
            },
            {
                "id": "measure",
                "name": "1234 (2).jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=measure",
            },
            {
                "id": "ambient",
                "name": "1234 ambiente.jpg",
                "mimeType": "image/jpeg",
                "url": "https://drive.google.com/uc?export=view&id=ambient",
            },
        ],
    )

    client = TestClient(app)
    response = client.get("/catalog/google-drive/photos", params={"code": "1234"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["white_background"].endswith("id=white")
    assert payload["measures"].endswith("id=measure")
    assert payload["ambient"].endswith("id=ambient")


def test_product_images_uses_google_drive_when_local_is_empty(monkeypatch):
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_FOLDER_ID", "drive-folder")
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_API_KEY", "test-key")
    monkeypatch.setattr("catalog.onedrive.find_local_images_for_code", lambda code: [])
    monkeypatch.setattr("catalog.onedrive.resolve_local_products_root", lambda: "D:/catalogo/fotos")
    monkeypatch.setattr(
        "catalog.google_drive.find_images_for_code",
        lambda code: [{"name": f"{code}.jpg", "variant": 0, "url": "https://drive.google.com/uc?export=view&id=file"}],
    )

    client = TestClient(app)
    response = client.get("/catalog/produtos/1234/imagens")

    assert response.status_code == 200
    payload = response.json()
    assert payload["codigo"] == "1234"
    assert payload["imagens"][0]["url"].endswith("id=file")


def test_google_drive_is_disabled_without_api_key(monkeypatch):
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_FOLDER_ID", "drive-folder")
    monkeypatch.delenv("CATALOG_GOOGLE_DRIVE_API_KEY", raising=False)

    from catalog import google_drive

    assert google_drive.is_configured() is False
