from fastapi.testclient import TestClient

from app import app


def test_s3_images_route_matches_product_code(monkeypatch):
    monkeypatch.setenv("CATALOG_S3_MEDIA_BUCKET", "catalog-images")
    monkeypatch.setenv("CATALOG_S3_MEDIA_PREFIX", "produtos/")
    monkeypatch.setenv("AWS_REGION", "sa-east-1")
    monkeypatch.setattr(
        "catalog.s3_media.list_s3_images",
        lambda bucket=None, prefix=None: [
            {
                "bucket": "catalog-images",
                "key": "produtos/1234 (1).jpg",
                "name": "1234 (1).jpg",
                "url": "https://catalog-images.s3.sa-east-1.amazonaws.com/produtos/1234%20%281%29.jpg",
            },
            {
                "bucket": "catalog-images",
                "key": "produtos/1234 ambiente.jpg",
                "name": "1234 ambiente.jpg",
                "url": "https://catalog-images.s3.sa-east-1.amazonaws.com/produtos/1234%20ambiente.jpg",
            },
            {
                "bucket": "catalog-images",
                "key": "produtos/9999.jpg",
                "name": "9999.jpg",
                "url": "https://catalog-images.s3.sa-east-1.amazonaws.com/produtos/9999.jpg",
            },
        ],
    )

    client = TestClient(app)
    response = client.get("/catalog/s3/produtos/1234/imagens")

    assert response.status_code == 200
    payload = response.json()
    assert payload["codigo"] == "1234"
    assert [item["name"] for item in payload["imagens"]] == ["1234 ambiente.jpg", "1234 (1).jpg"]


def test_s3_photos_route_categorizes_variants(monkeypatch):
    monkeypatch.setenv("CATALOG_S3_MEDIA_BUCKET", "catalog-images")
    monkeypatch.setattr(
        "catalog.s3_media.list_s3_images",
        lambda bucket=None, prefix=None: [
            {
                "name": "1234 (1).jpg",
                "url": "https://cdn.example.com/1234-white.jpg",
            },
            {
                "name": "1234 (2).jpg",
                "url": "https://cdn.example.com/1234-measures.jpg",
            },
            {
                "name": "1234 ambiente.jpg",
                "url": "https://cdn.example.com/1234-ambient.jpg",
            },
        ],
    )

    client = TestClient(app)
    response = client.get("/catalog/s3/photos", params={"code": "1234"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["white_background"].endswith("1234-white.jpg")
    assert payload["measures"].endswith("1234-measures.jpg")
    assert payload["ambient"].endswith("1234-ambient.jpg")


def test_product_images_uses_s3_before_google_drive(monkeypatch):
    monkeypatch.setenv("CATALOG_S3_MEDIA_BUCKET", "catalog-images")
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_FOLDER_ID", "drive-folder")
    monkeypatch.setenv("CATALOG_GOOGLE_DRIVE_API_KEY", "test-key")
    monkeypatch.setattr("catalog.onedrive.find_local_images_for_code", lambda code: [])
    monkeypatch.setattr("catalog.onedrive.resolve_local_products_root", lambda: "D:/catalogo/fotos")
    monkeypatch.setattr(
        "catalog.s3_media.find_images_for_code",
        lambda code: [{"name": f"{code}.jpg", "variant": 0, "url": "https://cdn.example.com/s3.jpg"}],
    )
    monkeypatch.setattr(
        "catalog.google_drive.find_images_for_code",
        lambda code: [{"name": f"{code}.jpg", "variant": 0, "url": "https://drive.google.com/file.jpg"}],
    )

    client = TestClient(app)
    response = client.get("/catalog/produtos/1234/imagens")

    assert response.status_code == 200
    assert response.json()["imagens"][0]["url"] == "https://cdn.example.com/s3.jpg"
