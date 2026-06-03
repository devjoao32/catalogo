from catalog.technical_specs import (
    clear_technical_specs_cache,
    get_technical_specs_for_code,
    load_technical_specs_map,
    resolve_technical_specs,
)


def test_load_technical_specs_map_normalizes_backslash_delimited_text(monkeypatch, tmp_path):
    specs_file = tmp_path / "technical_specs.txt"
    specs_file.write_text(
        "\n".join(
            [
                "CODIGO: 1580\\REFERENCIA: 1580\\POTENCIA(W): 7W\\BASE: E27\\GARANTIA: 2 anos",
                "CODIGO: 5991\\REFERENCIA: 5991\\POTENCIA MAXIMA: 40W\\BASE: E27\\GARANTIA: 1 ANO",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CATALOG_TECHNICAL_SPECS_PATH", str(specs_file))
    clear_technical_specs_cache()

    specs_map = load_technical_specs_map()
    assert specs_map["1580"] == "CODIGO: 1580 | REFERENCIA: 1580 | POTENCIA(W): 7W | BASE: E27 | GARANTIA: 2 anos"
    assert "5991" in specs_map
    assert get_technical_specs_for_code("5991").startswith("CODIGO: 5991 | REFERENCIA: 5991")


def test_load_technical_specs_prefers_longer_duplicate_entry(monkeypatch, tmp_path):
    specs_file = tmp_path / "technical_specs_duplicates.txt"
    specs_file.write_text(
        "\n".join(
            [
                "CODIGO: 1580\\POTENCIA(W): 7W",
                "CODIGO: 1580\\POTENCIA(W): 7W\\BASE: E27\\GARANTIA: 2 anos",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CATALOG_TECHNICAL_SPECS_PATH", str(specs_file))
    clear_technical_specs_cache()

    assert get_technical_specs_for_code("1580") == "CODIGO: 1580 | POTENCIA(W): 7W | BASE: E27 | GARANTIA: 2 anos"


def test_resolve_technical_specs_infers_profile_data_from_name(monkeypatch, tmp_path):
    specs_file = tmp_path / "empty_technical_specs.txt"
    specs_file.write_text("", encoding="utf-8")

    monkeypatch.setenv("CATALOG_TECHNICAL_SPECS_PATH", str(specs_file))
    clear_technical_specs_cache()

    specs = resolve_technical_specs(
        code="6141",
        name="PERFIL SOBREPOR PE007P 2M 23X26.7MM ALUM",
        description="PERFIL SOBREPOR PE007P 2M 23X26.7MM ALUM",
        category="PERFIL",
    )

    assert specs == "CODIGO: 6141 | REFERENCIA: PE007P | COMPRIMENTO: 2M | DIMENSOES: 23X26.7MM | MATERIAL: ALUMINIO"
