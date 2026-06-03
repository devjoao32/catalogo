# Modelo de Ficha Tecnica

O catalogo gera ficha tecnica em PDF pelo formato de exportacao `ficha`.

```text
GET /catalog/export?format=ficha&code=1578
```

O arquivo gerado usa o nome:

```text
ficha-tecnica-1578.pdf
```

## Estrutura Visual

- Cabecalho com marca, slogan e identidade visual.
- Bloco principal com categoria, nome comercial e codigo do produto.
- Descricao curta do produto.
- Imagem principal em destaque.
- Imagem ambientada quando existir.
- Area de medidas quando existir foto de medidas.
- Resumo rapido com potencia, tensao, protecao/base e temperatura de cor.
- Tabela de informacoes tecnicas.
- Rodape com site da marca.

## Campos Usados

Campos principais:

- `Codigo`
- `Nome`
- `Categoria`
- `Descricao`
- `Especificacoes`
- `URLFoto`
- `FotoBranco`
- `FotoAmbient`
- `FotoMedidas`
- `CODMARCA`

Campos tecnicos interpretados de `Especificacoes` ou atributos extras:

- Potencia
- Tensao
- Temperatura de cor
- Fluxo luminoso
- IRC
- Fator de potencia
- Angulo de abertura
- Grau de protecao
- Material
- Acabamento
- Medidas
- Peso
- Garantia

## Como Usar no Site

Na tela de detalhe do produto, o botao **Ficha tecnica** baixa o PDF diretamente para aquele item.

Os demais formatos continuam disponiveis:

- CSV
- Excel
- PDF
- ZIP
- JSON
