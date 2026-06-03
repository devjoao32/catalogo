from catalog.nitrolux_db import load_packaging_index, merge_products_with_nitrolux


def test_load_packaging_index_maps_rows(monkeypatch):
    monkeypatch.setenv("CATALOG_NITROLUX_DB_ENABLED", "true")
    monkeypatch.setenv("CATALOG_NITROLUX_DB_USER", "postgres")

    monkeypatch.setattr(
        "catalog.nitrolux_db._fetch_packaging_rows",
        lambda config, codes: [
            ("1001", "6", "24"),
            ("2002", None, 60),
            ("", "1", "2"),
        ],
    )

    index = load_packaging_index(["1001", "2002", "1001"])

    assert index == {
        "1001": {"Embalagem": "6", "CaixaMaster": "24"},
        "2002": {"CaixaMaster": "60"},
    }


def test_merge_products_with_nitrolux_enriches_matching_codes(monkeypatch):
    monkeypatch.setattr(
        "catalog.nitrolux_db.load_packaging_index",
        lambda codes: {
            "1001": {"Embalagem": "6", "CaixaMaster": "24"},
        },
    )

    merged = merge_products_with_nitrolux(
        [
            {"Codigo": "1001", "Nome": "Produto A"},
            {"Codigo": "2002", "Nome": "Produto B"},
        ]
    )

    assert merged[0]["Embalagem"] == "6"
    assert merged[0]["CaixaMaster"] == "24"
    assert "Embalagem" not in merged[1]


def test_merge_products_with_nitrolux_preserves_existing_values_when_db_is_empty(monkeypatch):
    monkeypatch.setattr(
        "catalog.nitrolux_db.load_packaging_index",
        lambda codes: {
            "1001": {"CaixaMaster": "48"},
        },
    )

    merged = merge_products_with_nitrolux(
        [
            {"Codigo": "1001", "Nome": "Produto A", "Embalagem": "12"},
        ]
    )

    assert merged[0]["Embalagem"] == "12"
    assert merged[0]["CaixaMaster"] == "48"
