# Catalogo de Produtos

API em FastAPI + frontend React (Vite + TypeScript) para:
- listar produtos locais (OneDrive/pasta local)
- buscar dados de Google Sheets
- servir imagens de produto
- consultar imagens via Microsoft Graph (opcional)

## Estrutura do Projeto

```text
catalog/      Backend FastAPI e regras de catalogo
frontend/     Aplicacao React/Vite e assets publicos
tests/        Testes automatizados do backend
scripts/      Utilitarios de manutencao
reports/      Dados e relatorios usados em desenvolvimento/local
docs/         Documentacao complementar do projeto
.codex-tmp/   Artefatos temporarios locais ignorados pelo Git
```

## Requisitos
- Python 3.10+
- Node.js 20+
- `pip`
- (Opcional) credenciais Azure para rotas Graph

## Instalacao Rapida

Backend:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:
```powershell
cd frontend
npm.cmd install
```

## Executar em Desenvolvimento

Terminal 1 (API):
```powershell
python app.py
```

Terminal 2 (frontend Vite):
```powershell
cd frontend
npm.cmd run dev
```

Aplicacao disponivel em:
- API: `http://127.0.0.1:8000`
- Frontend dev: `http://127.0.0.1:5173`

## Build do Frontend para Servir no FastAPI

```powershell
cd frontend
npm.cmd run build
```

Quando `frontend/dist/index.html` existe, o FastAPI serve automaticamente o build.
Se o build nao existir, a aplicacao usa fallback em `frontend/legacy`.

## Deploy AWS Serverless

O projeto tambem possui base para rodar em arquitetura serverless com S3 + API Gateway + Lambda, com Cognito e DynamoDB provisionados para a proxima etapa:

```powershell
python scripts/check_production_readiness.py --env-file .env.production --frontend-env frontend/.env.production
sam build
sam deploy --guided
```

Veja o passo a passo em `docs/aws-serverless.md`.

## Variaveis de Ambiente

Config geral:
- `CATALOG_HOST` (padrao: `127.0.0.1`)
- `CATALOG_PORT` (padrao: `8000`)
- `CATALOG_ENABLE_API_DOCS` (opcional, padrao: `true`; quando `false`, desabilita `/docs`, `/redoc` e `/openapi.json`)
- `CATALOG_CORS_ALLOW_ORIGINS` (csv, padrao local seguro: `http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5000,http://localhost:5000`)
- `CATALOG_CORS_ALLOW_CREDENTIALS` (padrao: `true`)
- `CATALOG_LOG_LEVEL` (opcional, padrao: `INFO`)
- `CATALOG_LOG_FORMAT` (opcional, formato padrao com timestamp, nivel e logger)
- `CATALOG_EXPORT_MAX_REMOTE_IMAGE_BYTES` (opcional, padrao: `5242880`; limite para baixar imagens remotas em exportacoes)

Frontend (Vite):
- `VITE_API_BASES` (csv; padrao: `,http://127.0.0.1:8000,http://127.0.0.1:5000`)
- `VITE_REQUEST_TIMEOUT_MS` (padrao: `12000`)
- `VITE_DEV_PROXY_TARGET` (padrao: `http://127.0.0.1:8000`)

Dados locais:
- `CATALOG_LOCAL_PRODUCTS_PATH` (opcional, caminho explicito da pasta de produtos)
- `CATALOG_LOCAL_PRODUCTS_HOME_FALLBACK` (opcional, padrao: `true`; controla fallback automatico para `~/OneDrive`)
- `CATALOG_CADASTRO_HTML` (opcional, caminho explicito do `CADASTRO.html`)
- `CATALOG_ERP_JSON_PATH` (opcional, caminho do arquivo JSON espelho do ERP)
- `CATALOG_ERP_INBOX_DIR` (opcional, pasta para armazenar arquivos recebidos em `/catalog/erp/upload`)
- `CATALOG_ERP_ADMIN_TOKEN` (opcional; quando definido, protege `/catalog/erp/*` e exige `X-Catalog-Admin-Token` ou `Authorization: Bearer <token>`)
- `CATALOG_ADMIN_LOGIN_EMAIL` (opcional; e-mail autorizado para login local no painel interno)
- `CATALOG_ADMIN_LOGIN_PASSWORD` (opcional; senha do login local no painel interno)
- `CATALOG_ADMIN_USERS_FILE` (opcional; caminho de um JSON com varios administradores; por padrao usa `reports/admin_users.json`)
- `CATALOG_REPRESENTATIVE_LOGIN_EMAIL` (opcional; login unico de representante)
- `CATALOG_REPRESENTATIVE_LOGIN_PASSWORD` (opcional; senha do login unico de representante)
- `CATALOG_REPRESENTATIVE_LOGIN_NAME` (opcional; nome exibido para o login unico)
- `CATALOG_REPRESENTATIVE_USERS_JSON` (opcional; JSON com varios representantes, ex.: `[{"email":"rep1@empresa.com","password":"senha","name":"Rep 1"}]`)
- `CATALOG_REPRESENTATIVE_JWT_SECRET` (opcional; segredo dedicado para assinar o JWT dos representantes; por padrao reutiliza `CATALOG_SESSION_SECRET`)
- `CATALOG_REPRESENTATIVE_JWT_EXPIRES_MINUTES` (opcional, padrao: `720`; expiracao do JWT dos representantes)
- `CATALOG_SESSION_SECRET` (obrigatorio em producao; segredo usado para assinar a sessao do painel administrativo e, se `CATALOG_REPRESENTATIVE_JWT_SECRET` nao for definido, os JWTs dos representantes. Em desenvolvimento sem variavel definida, um segredo temporario e gerado por processo.)
- `CATALOG_SESSION_MAX_AGE_SECONDS` (opcional, padrao: `43200`; duracao da sessao do painel administrativo)
- `CATALOG_SESSION_COOKIE_SECURE` (opcional, recomendado `true` em HTTPS/producao; marca o cookie administrativo como Secure)
- `CATALOG_ERP_MAX_UPLOAD_BYTES` (opcional, padrao: `10485760`; limite do payload em `/catalog/erp/upload`)
- `CATALOG_ERP_SOURCE_DIRS` (opcional, lista CSV de pastas adicionais para descoberta automatica de JSON)
- `CATALOG_ERP_AUTO_DISCOVERY` (opcional, padrao: `true`; quando `false`, desabilita a descoberta automatica de JSON ERP fora do caminho configurado)
- `CATALOG_ERP_STRICT_MODE` (opcional, padrao: `true`; quando ativo, o catalogo exibe somente codigos presentes no JSON ERP atual)
- `CATALOG_STOCK_REPORT_PATH` (opcional, caminho explicito de uma planilha `POSICAO_ESTOQUE`)
- `CATALOG_STOCK_REPORT_AUTO_DISCOVERY` (opcional, padrao: `true`; quando `false`, nao procura planilhas automaticamente em `reports/`)
- `CATALOG_STOCK_PHOTOS_ROOT` (opcional, caminho explicito da raiz de fotos do estoque)
- `CATALOG_STOCK_PHOTOS_HOME_FALLBACK` (opcional, padrao: `true`; controla fallback automatico para `~/OneDrive/MARKETING/01_PRODUTOS`)
  - Se nao informar, o backend tenta detectar automaticamente arquivos como `erp*.json` ou `pcprodut*.json` na raiz do projeto, em `reports/`, em `reports/erp_inbox` e em `catalog/json/`.
  - Se `CATALOG_ERP_JSON_PATH` estiver configurado mas o arquivo nao existir, o backend faz fallback automatico para essa descoberta.

Google Drive de fotos (opcional):
- `CATALOG_GOOGLE_DRIVE_FOLDER_ID` (ID ou URL da pasta raiz compartilhada com as fotos)
- `CATALOG_GOOGLE_DRIVE_API_KEY` (chave usada para listar os arquivos pela API do Drive)
- `CATALOG_GOOGLE_DRIVE_RECURSIVE` (opcional, padrao: `true`; busca tambem em subpastas)
- `CATALOG_GOOGLE_DRIVE_MAX_DEPTH` (opcional, padrao: `4`; profundidade maxima em subpastas)
  - As fotos devem ter o codigo no nome do arquivo. Exemplos aceitos: `1234.jpg`, `1234 (1).jpg`, `1234 (2).jpg`, `1234 ambiente.jpg`.
  - A rota `/catalog/google-drive/photos?code=1234` retorna as fotos principais categorizadas.
  - A rota `/catalog/google-drive/produtos/1234/imagens` retorna a galeria completa encontrada no Drive.

Amazon S3 de fotos (opcional/recomendado em producao):
- `CATALOG_S3_MEDIA_BUCKET` (bucket onde ficam as imagens dos produtos)
- `CATALOG_S3_MEDIA_PREFIX` (opcional, prefixo dentro do bucket; ex.: `produtos/`)
- `CATALOG_S3_MEDIA_PUBLIC_BASE_URL` (opcional, URL publica ou CloudFront para montar URLs das imagens)
- `CATALOG_S3_MEDIA_PRESIGNED_URLS` (opcional, padrao: `false`; quando `true`, gera URLs pre-assinadas)
- `CATALOG_S3_MEDIA_PRESIGNED_EXPIRES_SECONDS` (opcional, padrao: `3600`)
  - A rota `/catalog/s3/photos?code=1234` retorna fotos principais categorizadas.
  - A rota `/catalog/s3/produtos/1234/imagens` retorna a galeria completa encontrada no S3.
  - As rotas principais do catalogo tentam local, depois S3, depois Google Drive/Graph.

PostgreSQL Nitrolux (opcional):
- `CATALOG_NITROLUX_DB_ENABLED` (opcional, padrao: `false`)
- `CATALOG_NITROLUX_DB_URL` (opcional; string de conexao completa)
- `CATALOG_NITROLUX_DB_HOST` (padrao: `127.0.0.1`)
- `CATALOG_NITROLUX_DB_PORT` (padrao: `5432`)
- `CATALOG_NITROLUX_DB_NAME` (padrao: `nitrolux`)
- `CATALOG_NITROLUX_DB_USER`
- `CATALOG_NITROLUX_DB_PASSWORD`
- `CATALOG_NITROLUX_DB_SSLMODE` (opcional, padrao: `prefer`)
- `CATALOG_NITROLUX_DB_SCHEMA` (opcional, padrao: `public`)
- `CATALOG_NITROLUX_DB_TABLE` (opcional, padrao: `pcprodut`)
- `CATALOG_NITROLUX_DB_CODE_COLUMN` (opcional, padrao: `codprod`)
- `CATALOG_NITROLUX_DB_PACKAGE_COLUMN` (opcional, padrao: `embalagem`)
- `CATALOG_NITROLUX_DB_MASTER_BOX_COLUMN` (opcional, padrao: `caixa_master`)
  - Quando habilitado, o backend enriquece cada produto com `Embalagem` e `CaixaMaster` usando o codigo do produto.
  - Se a tabela ou os nomes das colunas no seu banco forem diferentes, basta sobrescrever essas variaveis.

Azure / Graph (opcional):
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`
- `AZURE_REDIRECT_URI`
- `CATALOG_TOKEN_CACHE_FILE` (opcional; sobrescreve o caminho do cache persistente de token OAuth)

## Endpoints Principais

API e frontend:
- `GET /` (SPA/frontend)
- `GET /catalog/sheet?url=<GOOGLE_SHEET_URL>`
- `GET /catalog/photos?code=<CODIGO>&shareUrl=<ONEDRIVE_SHARE_URL>`
- `GET /catalog/produtos/{codigo}/imagens?shareUrl=<ONEDRIVE_SHARE_URL>`
- `GET /catalog/local/produtos`
- `GET /catalog/local/asset?path=<CAMINHO_RELATIVO>`
- `GET /catalog/export?format=ficha&code=<CODIGO>` (gera a ficha tecnica em PDF de um produto)
- `POST /catalog/erp/import` (importa JSON do ERP e atualiza os dados por codigo)
- `POST /catalog/erp/upload?filename=<NOME_ARQUIVO>` (recebe JSON bruto no corpo da requisicao)
- `POST /catalog/erp/import-file` (importa arquivo JSON ja depositado no backend)
- `GET /catalog/erp/files` (lista arquivos JSON ERP encontrados)
- `GET /catalog/erp/status` (status da carga ERP atual)

Autenticacao:
- `GET /auth/login`
- `GET /auth/callback`
- `GET /auth/session`
- `POST /auth/admin/login`
- `GET /auth/representative/session`
- `POST /auth/representative/login`
- `POST /auth/representative/logout`
- `POST /auth/logout`

## Painel Interno

O painel administrativo de JSON fica na rota `/erp` e agora pode operar com sessao
de navegador. Quando `CATALOG_ERP_ADMIN_TOKEN` estiver definido, o backend aceita:
- login por sessao no navegador via `POST /auth/admin/login`
- uso tecnico do token por header (`X-Catalog-Admin-Token` ou `Authorization: Bearer`)

Quando `CATALOG_ADMIN_LOGIN_EMAIL` e `CATALOG_ADMIN_LOGIN_PASSWORD` estiverem definidos,
o painel exige esse login local por e-mail e senha para abrir a area interna.

Se o login Microsoft estiver configurado (`AZURE_*` + `AZURE_REDIRECT_URI`),
o callback OAuth tambem cria uma sessao administrativa para o painel.

## Acesso de Representantes

Quando `CATALOG_REPRESENTATIVE_USERS_JSON` ou `CATALOG_REPRESENTATIVE_LOGIN_*` estiverem
definidos, o catalogo principal passa a exigir login em `/login`.

- o backend emite um JWT assinado para o representante autenticado
- o JWT tambem e gravado em cookie HTTP-only para manter fotos, galerias e exportacoes funcionando no navegador
- as rotas do catalogo (`/catalog/local/produtos`, `/catalog/photos`, `/catalog/produtos/*`, `/catalog/export` e `/catalog/local/asset`) passam a exigir esse acesso

## Importacao JSON do ERP

O catalogo le o JSON do ERP diretamente no backend (sem upload na pagina web).
Com `CATALOG_ERP_JSON_PATH` configurado para `D:/catalogo/pcprodut_20260309_115420.json`,
os produtos sao enriquecidos automaticamente por `Codigo`, incluindo itens sem foto
(com placeholder) e organizacao por categoria.
Categorias tecnicas (`CODEPTO/CODSEC`) sao convertidas para nomes comerciais
quando houver mapeamento configurado no backend.
Atualmente o catalogo padroniza em grupos de negocio como:
`ILUMINACAO DECORATIVA`, `ILUMINACAO TECNICA`, `ILUMINACAO EXTERNA E PUBLICA`,
`LAMPADAS E FITAS`, `COMPONENTES E ACESSORIOS`, `UTILIDADES E OPERACAO`
e `OUTROS ITENS ERP`.

Se precisar importar manualmente um novo payload pela API:

```powershell
curl -X POST http://127.0.0.1:8000/catalog/erp/import `
  -H "Content-Type: application/json" `
  -d "{\"products\":[{\"codigo\":\"1234\",\"nome\":\"Produto ERP\",\"categoria\":\"PENDENTE\"}]}"
```

Para receber um arquivo JSON bruto no backend (sem upload em formulario web):

```powershell
curl -X POST "http://127.0.0.1:8000/catalog/erp/upload?filename=pcprodut_20260309_115420.json" `
  -H "Content-Type: application/json" `
  --data-binary "@D:/Catalogo/pcprodut_20260309_115420.json"
```

Para processar um arquivo ja depositado no servidor:

```powershell
curl -X POST "http://127.0.0.1:8000/catalog/erp/import-file" `
  -H "Content-Type: application/json" `
  -d "{\"file_path\":\"reports/pcprodut_20260309_115420.json\"}"
```

## Estrutura do Projeto
```text
.
|-- app.py
|-- frontend/
|   |-- src/
|   |-- public/
|   |-- legacy/
|   `-- dist/ (gerado no build)
|-- catalog/
|   |-- bootstrap.py
|   |-- auth.py
|   |-- routes.py
|   |-- onedrive.py
|   |-- spreadsheet.py
|   |-- cadastro.py
|   |-- cache.py
|   |-- graph_client.py
|   |-- api/
|   |   |-- __init__.py
|   |   |-- router.py
|   |   `-- frontend.py
|   `-- core/
|       |-- __init__.py
|       `-- settings.py
`-- tests/
```

## Testes
```powershell
pytest -q
```

## Observacoes
- O frontend principal usa React Router + TanStack Query.
- O frontend legado permanece em `frontend/legacy` como fallback.
- Se credenciais Azure nao estiverem configuradas, rotas de fotos podem operar em modo local/alternativo.
