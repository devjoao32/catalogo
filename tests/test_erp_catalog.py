import os

from catalog.erp_catalog import get_erp_status, import_erp_payload, merge_products_with_erp
from catalog.technical_specs import clear_technical_specs_cache


def test_merge_products_with_erp_data(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_merge.json')
    if os.path.exists(target_path):
        os.remove(target_path)


def test_merge_products_maps_to_specific_categories(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_business_map.json')
    if os.path.exists(target_path):
        os.remove(target_path)


def test_import_erp_payload_tracks_change_summary(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_changes.json')
    if os.path.exists(target_path):
        os.remove(target_path)


def test_merge_products_prefers_ambient_cover(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_cover_priority.json')
    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {
                    'codigo': '6100',
                    'nome': 'Pendente Premium',
                    'categoria': 'PENDENTE',
                    'urlfoto': 'https://example.com/6100_1.jpg',
                    'fotobranco': 'https://example.com/6100_1.jpg',
                    'fotoambient': 'https://example.com/6100_3.jpg',
                    'fotomedidas': 'https://example.com/6100_2.jpg',
                }
            ]
        }
    )

    merged = merge_products_with_erp([])
    assert len(merged) == 1
    assert merged[0]['Codigo'] == '6100'
    assert merged[0]['URLFoto'] == 'https://example.com/6100_3.jpg'
    assert merged[0]['FotoBranco'] == 'https://example.com/6100_1.jpg'
    assert merged[0]['FotoAmbient'] == 'https://example.com/6100_3.jpg'
    assert merged[0]['FotoMedidas'] == 'https://example.com/6100_2.jpg'

    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {'codigo': '1001', 'nome': 'Produto Base', 'categoria': 'PENDENTE'},
                {'codigo': '2002', 'nome': 'Produto Removido', 'categoria': 'ARANDELA'},
            ]
        }
    )

    result = import_erp_payload(
        {
            'products': [
                {'codigo': '1001', 'nome': 'Produto Base Atualizado', 'categoria': 'PENDENTE'},
                {'codigo': '3003', 'nome': 'Produto Novo', 'categoria': 'LUMINARIA'},
            ]
        }
    )

    summary = result['last_change_summary']
    assert summary['added_count'] == 1
    assert summary['updated_count'] == 1
    assert summary['removed_count'] == 1
    assert summary['unchanged_count'] == 0
    assert any(change['code'] == '1001' and 'Nome' in change['changed_fields'] for change in summary['changes'])
    assert any(change['code'] == '3003' and change['change_type'] == 'added' for change in summary['changes'])
    assert any(change['code'] == '2002' and change['change_type'] == 'removed' for change in summary['changes'])

    status = get_erp_status()
    assert status['last_change_summary']['updated_count'] == 1

    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {'codigo': '3003', 'nome': 'Produto Painel', 'categoria': 'PAINEL'},
                {'codigo': '4004', 'nome': 'Produto Balizador', 'categoria': 'BALIZADOR'},
                {'codigo': '5005', 'nome': 'Produto Rele', 'descricao': 'RELE FOTOCELULA'},
                {'codigo': '6006', 'nome': 'Produto Sem Grupo', 'categoria': 'GRUPO X'},
            ]
        }
    )

    merged = merge_products_with_erp([])

    allowed = {
        'PAINEL',
        'BALIZADOR',
        'RELE',
        'OUTROS ITENS ERP',
    }

    categories = {item['Categoria'] for item in merged}
    assert categories.issubset(allowed)

    product_3003 = next(item for item in merged if item['Codigo'] == '3003')
    assert product_3003['Categoria'] == 'PAINEL'

    product_4004 = next(item for item in merged if item['Codigo'] == '4004')
    assert product_4004['Categoria'] == 'BALIZADOR'

    product_5005 = next(item for item in merged if item['Codigo'] == '5005')
    assert product_5005['Categoria'] == 'RELE'

    product_6006 = next(item for item in merged if item['Codigo'] == '6006')
    assert product_6006['Categoria'] == 'OUTROS ITENS ERP'

    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {
                    'codigo': '1001',
                    'nome': 'Produto ERP 1001',
                    'categoria': 'PENDENTE',
                    'descricao': 'Descricao ERP 1001',
                    'voltagem': '220V',
                },
                {
                    'codigo': '2002',
                    'nome': 'Produto ERP 2002',
                    'categoria': 'LUMINARIA',
                },
            ]
        }
    )

    base_products = [
        {
            'Codigo': '1001',
            'Nome': 'Produto Local 1001',
            'Descricao': '',
            'Categoria': 'Sem categoria',
            'URLFoto': '/catalog/local/asset?path=1001.jpg',
            'Especificacoes': '',
            'FotoBranco': '/catalog/local/asset?path=1001.jpg',
            'FotoAmbient': '',
            'FotoMedidas': '',
        }
    ]

    merged = merge_products_with_erp(base_products)
    assert len(merged) == 2

    product_1001 = next(item for item in merged if item['Codigo'] == '1001')
    assert product_1001['Nome'] == 'Produto ERP 1001'
    assert product_1001['Categoria'] == 'PENDENTE'
    assert product_1001['Descricao'] == 'Descricao ERP 1001'
    # Mantem foto local quando o ERP nao envia URL.
    assert product_1001['URLFoto'].startswith('/catalog/local/asset')
    assert product_1001['voltagem'] == '220V'

    product_2002 = next(item for item in merged if item['Codigo'] == '2002')
    assert product_2002['Nome'] == 'Produto ERP 2002'
    assert product_2002['Categoria'] == 'LUMINARIA'
    assert product_2002['URLFoto'].startswith('https://placehold.co/')

    if os.path.exists(target_path):
        os.remove(target_path)


def test_merge_products_with_erp_fills_specs_from_technical_specs(monkeypatch, tmp_path):
    target_path = tmp_path / "_test_erp_specs.json"
    specs_file = tmp_path / "technical_specs.txt"
    specs_file.write_text(
        "CODIGO: 1580\\REFERENCIA: 1580\\POTENCIA(W): 7W\\BASE: E27\\GARANTIA: 2 anos",
        encoding="utf-8",
    )

    monkeypatch.setenv("CATALOG_ERP_JSON_PATH", str(target_path))
    monkeypatch.setenv("CATALOG_TECHNICAL_SPECS_PATH", str(specs_file))
    clear_technical_specs_cache()

    import_erp_payload(
        {
            "products": [
                {"codigo": "1580", "nome": "Lampada ERP 1580", "categoria": "LAMPADAS BULBO"},
            ]
        }
    )

    merged = merge_products_with_erp([])
    assert len(merged) == 1
    assert merged[0]["Codigo"] == "1580"
    assert merged[0]["Especificacoes"] == "CODIGO: 1580 | REFERENCIA: 1580 | POTENCIA(W): 7W | BASE: E27 | GARANTIA: 2 anos"


def test_merge_products_with_erp_infers_specs_when_code_is_missing_from_file(monkeypatch, tmp_path):
    target_path = tmp_path / "_test_erp_inferred_specs.json"
    specs_file = tmp_path / "technical_specs.txt"
    specs_file.write_text("", encoding="utf-8")

    monkeypatch.setenv("CATALOG_ERP_JSON_PATH", str(target_path))
    monkeypatch.setenv("CATALOG_TECHNICAL_SPECS_PATH", str(specs_file))
    clear_technical_specs_cache()

    import_erp_payload(
        {
            "products": [
                {
                    "codigo": "6141",
                    "nome": "PERFIL SOBREPOR PE007P 2M 23X26.7MM ALUM",
                    "categoria": "PERFIL",
                },
            ]
        }
    )

    merged = merge_products_with_erp([])
    assert len(merged) == 1
    assert merged[0]["Codigo"] == "6141"
    assert merged[0]["Especificacoes"] == "CODIGO: 6141 | REFERENCIA: PE007P | COMPRIMENTO: 2M | DIMENSOES: 23X26.7MM | MATERIAL: ALUMINIO"
