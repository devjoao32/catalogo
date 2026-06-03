# Deploy AWS Serverless

Este projeto foi preparado para a arquitetura:

- Frontend React/Vite em Amazon S3
- Backend FastAPI em AWS Lambda
- API Gateway HTTP API na frente da Lambda
- Fotos de produtos em Amazon S3
- Cognito provisionado para a proxima etapa de autenticacao
- DynamoDB provisionado para a futura migracao dos dados persistidos

## Pre-requisitos

- AWS CLI configurado com uma conta e regiao
- AWS SAM CLI instalado
- Python 3.12
- Node.js 20

## 1. Build e deploy da API

Na raiz do projeto:

Prepare as variaveis de producao fora do Git usando `.env.production.example` como modelo.
Antes do deploy, rode:

```powershell
python scripts/check_production_readiness.py `
  --env-file .env.production `
  --frontend-env frontend/.env.production
```

O comando deve terminar com `Production readiness check passed.`.

```powershell
sam build
sam deploy --guided `
  --parameter-overrides `
    StageName=prod `
    CorsAllowOrigins=https://SEU_BUCKET.s3-website-SA-EAST-1.amazonaws.com `
    CatalogSessionSecret=um-segredo-unico-com-mais-de-32-caracteres `
    GoogleDriveFolderId=1VTM0VHyMXpy1luya-hG2jXK5sqaKYVgX `
    GoogleDriveApiKey=SUA_GOOGLE_DRIVE_API_KEY `
    MediaPrefix=produtos/
```

Ao final, copie os outputs `ApiUrl`, `FrontendBucket` e `MediaBucketName`.

## 2. Enviar as fotos para o S3

Use o bucket retornado em `MediaBucketName`. O exemplo abaixo envia a pasta local atual para o prefixo `produtos/`:

```powershell
aws s3 sync "C:\Users\joao.silva\OneDrive\TI 1\catalogo\Flayer" s3://NOME_DO_BUCKET/produtos/ --delete
```

As imagens devem manter o codigo no nome do arquivo, por exemplo:

- `1578 - LAMP LED A60 BULBO 9W BIVOLT 6500K E27 (1).jpg`
- `1583 - LAMPADA BULBO A60 9W 3000K.jpg`
- `3126 3127 - LUMINARIA LED TRILHO.jpg`

A API passa a buscar primeiro nas fotos locais quando rodar na sua maquina, depois no S3, depois no Google Drive.

Rotas diretas para validar o S3:

```text
/catalog/s3/photos?code=1578
/catalog/s3/produtos/1578/imagens
```

## 3. Build do frontend apontando para a API

Crie `frontend/.env.production` com:

```env
VITE_API_BASES=https://SEU_API_ID.execute-api.SUA_REGIAO.amazonaws.com/prod
VITE_REQUEST_TIMEOUT_MS=12000
```

Depois rode:

```powershell
cd frontend
npm ci
npm run build
```

## 4. Publicar frontend no S3

Use o bucket retornado no output `FrontendBucket`:

```powershell
aws s3 sync dist s3://NOME_DO_BUCKET --delete
```

Abra o output `FrontendWebsiteUrl`.

## Observacoes importantes

- A pasta local `C:\Users\joao.silva\OneDrive\TI 1\catalogo\Flayer` funciona na sua maquina, mas nao existe dentro da Lambda. Em producao serverless, sincronize essa pasta com o bucket `MediaBucketName`.
- O Google Drive segue integrado como fonte remota alternativa, mas em producao o S3 passa a ser a fonte principal recomendada.
- Use `CATALOG_SESSION_COOKIE_SECURE=true` quando o frontend/API estiverem em HTTPS.
- Nao reutilize exemplos de segredo em producao. Gere valores longos e unicos para `CatalogSessionSecret` e, se usado, `CATALOG_REPRESENTATIVE_JWT_SECRET`.
- Como S3 Website e API Gateway usam dominios diferentes, fluxos baseados em cookie podem exigir um dominio proprio com CloudFront para frontend/API ficarem no mesmo site. A alternativa mais limpa e migrar a autenticacao para Cognito na proxima etapa.
- O Cognito e o DynamoDB ja ficam provisionados no stack, mas a aplicacao ainda usa os fluxos atuais de autenticacao e dados. A migracao completa para Cognito/DynamoDB deve ser feita em uma segunda etapa para nao misturar deploy com mudanca de regra de negocio.
